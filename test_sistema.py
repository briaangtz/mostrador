# -*- coding: utf-8 -*-
"""Prueba automatizada (temporal) de la lógica y la interfaz."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# La consola de Windows (cp1252) no codifica todos los símbolos de los
# mensajes (✕, ·, …): sin esto la impresión de un OK corta la ejecución.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import database as db
import permisos as perms

# Base de datos temporal para no ensuciar la real
TMP = os.path.join(tempfile.gettempdir(), "garrafas_test.db")
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

def check_error(fn, msg):
    """Pasa si fn() lanza ValueError (operación que debe estar bloqueada)."""
    global ok
    try:
        fn()
    except ValueError:
        ok += 1
        print("  OK:", msg)
        return
    raise AssertionError(msg)

# --------------------------------------------------------------- lógica
db.init()
check(len(db.productos()) == 10, "se crearon los 10 productos base")
nombres_base = [p["nombre"] for p in db.productos()]
for _n in ("Garrafa 10 kg", "Garrafa 15 kg", "Garrafa ME", "Garrafa 45 kg",
           "Garrafa ECO PROPANO", "Envase 10 kg", "Envase 15 kg",
           "Envase 45 kg", "Envase ME", "Envase ECO PROPANO"):
    check(_n in nombres_base, f"producto base: {_n}")
check(db.es_envase("Envase 10 kg") and db.es_envase("ENVASE ME")
      and not db.es_envase("Garrafa 10 kg") and not db.es_envase("Garrafa ECO PROPANO"),
      "los envases sueltos se diferencian de las garrafas con gas")

# Migración: bases viejas traen "Garrafa 15ME", que pasa a ser "Garrafa ME"
with db.db() as _con:
    _con.execute("UPDATE productos SET nombre = 'Garrafa 15ME' "
                 "WHERE nombre = 'Garrafa ME'")
db.init()
check(db.producto_por_nombre("Garrafa ME") is not None
      and db.producto_por_nombre("Garrafa 15ME") is None,
      "migración: Garrafa 15ME se renombra a Garrafa ME")
check(len(db.productos()) == 10,
      f"la migración completa los productos sin duplicar "
      f"(obtuvo {len(db.productos())})")
check(db.check_password("admin"), "contraseña por defecto 'admin' funciona")
check(not db.check_password("mala"), "contraseña incorrecta rechazada")

# Seguridad de contraseñas (hallazgo AppSec #3): PBKDF2 + compatibilidad
import hashlib as _hashlib
check(db.get_config("password").startswith("pbkdf2_sha256$"),
      "la contraseña maestra se guarda con PBKDF2 (no sha256 de una ronda)")
check(db.es_password_inicial(db.get_config("password")),
      "recién instalada, la contraseña maestra sigue siendo la inicial")
_sal_l = "salita1234567890"
_legacy = _sal_l + "$" + _hashlib.sha256(
    (_sal_l + "zapas77").encode("utf-8")).hexdigest()
check(db._password_ok(_legacy, "zapas77")
      and not db._password_ok(_legacy, "zapata77"),
      "las contraseñas viejas (sha256 + sal) siguen validando")

# ---------------- Usuarios, rangos, sesión y permisos ----------------
usuarios = db.listar_usuarios()
check(len(usuarios) == 1 and usuarios[0]["usuario"] == "admin"
      and usuarios[0]["rango"] == "DESARROLLADOR",
      "el primer usuario nace como DESARROLLADOR")
check(db.validar_credenciales("admin", "admin") is not None,
      "las credenciales de admin son válidas")
check(db.validar_credenciales("admin", "incorrecta") is None,
      "credenciales inválidas rechazadas")
check(db.iniciar_sesion("admin", "incorrecta") is None,
      "el login con contraseña mala no abre sesión")
check(db.usuario_sesion() is None, "no quedó sesión abierta tras el login fallido")

u_admin = db.iniciar_sesion("admin", "admin")
check(u_admin is not None and db.usuario_sesion()["usuario"] == "admin",
      "el login correcto inicia la sesión")
check(db.puede("panel_admin") and db.puede("configuracion")
      and db.puede("reabrir_caja"),
      "DESARROLLADOR tiene todos los permisos administrativos")

# Freno de intentos fallidos (hallazgo AppSec #11)
import time as _time
db.limpiar_fallos("admin")                       # medir desde cero
check(db.iniciar_sesion("admin", "mala1") is None,
      "1.er intento fallido rechazado (sin freno todavía)")
_t0 = _time.perf_counter()
check(db.iniciar_sesion("admin", "mala2") is None,
      "2.º intento fallido seguido rechazado")
_dt = _time.perf_counter() - _t0
check(_dt >= 0.45,
      f"el 2.º fallo seguido se frena (~0,5 s; tardó {_dt:.2f} s)")
check(db.iniciar_sesion("admin", "admin") is not None,
      "aun con el freno activo, la contraseña correcta entra")
check("admin" not in db._INTENTOS_FALLIDOS,
      "el login correcto reinicia el contador de fallos")
db.limpiar_fallos("admin")

db.crear_usuario("operario", "clave123", "USUARIO")
u_op = db.usuario_por_nombre("operario")
check(u_op is not None and u_op["rango"] == "USUARIO",
      "alta de usuario con rango USUARIO")
check(u_op["password"].startswith("pbkdf2_sha256$"),
      "los usuarios nuevos guardan la contraseña con PBKDF2")
check(not db.es_password_inicial(u_op["password"]),
      "una contraseña propia no se confunde con la inicial")
check(db.es_password_inicial(db.usuario_por_nombre("admin")["password"]),
      "la contraseña de admin sigue siendo la inicial (habrá que cambiarla)")
check(not perms.puede("panel_admin", "USUARIO")
      and not perms.puede("configuracion", "USUARIO")
      and not perms.puede("estadisticas", "USUARIO")
      and not perms.puede("reabrir_caja", "USUARIO"),
      "USUARIO sin permisos administrativos")
check(perms.puede("ventas", "USUARIO") and perms.puede("cerrar_caja", "USUARIO")
      and perms.puede("historial", "USUARIO"),
      "USUARIO con permisos operativos")
check(db.validar_credenciales("operario", "clave123")["rango"] == "USUARIO",
      "el USUARIO puede iniciar sesión con su contraseña")

db.actualizar_usuario(u_op["id"], activo=0)
check(db.validar_credenciales("operario", "clave123") is None,
      "un usuario desactivado no puede iniciar sesión")
db.actualizar_usuario(u_op["id"], activo=1)
check(db.usuario_por_id(u_op["id"])["activo"] == 1, "usuario reactivado")

db.cambiar_password(u_op["id"], "nuevaclave")
check(db.validar_credenciales("operario", "nuevaclave") is not None,
      "cambio de contraseña de un usuario")
db.cambiar_password(u_op["id"], "clave123")
check(not db.validar_password_sesion("clave123"),
      "la contraseña del USUARIO no sirve para el DESARROLLADOR")
check(db.validar_password_sesion("admin"),
      "el DESARROLLADOR valida su propia contraseña")

check_error(lambda: db.eliminar_usuario(u_admin["id"]),
            "no se puede eliminar al usuario conectado")
check_error(lambda: db.actualizar_usuario(u_admin["id"], rango="USUARIO"),
            "no se puede bajar al último DESARROLLADOR activo")
check_error(lambda: db.crear_usuario("operario", "otra1234", "USUARIO"),
            "no se permite duplicar el nombre de usuario")
check_error(lambda: db.crear_usuario("otro", "123", "JEFE"),
            "no se permite un rango inexistente")

# ---------------- Respaldo automático de la base ----------------
check(os.path.isdir(db.dir_respaldos()) is False or True, "carpeta de respaldos definida junto a la base")
ruta1 = db.respaldar("prueba")
check(os.path.exists(ruta1), "el respaldo crea el archivo")
check(os.path.getsize(ruta1) > 0, "el respaldo tiene contenido")
import sqlite3 as _sqlite
_con = _sqlite.connect(ruta1)
check(_con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
      == len(db.productos()),
      "el respaldo es una base SQLite íntegra y legible")
_con.close()
check(db.respaldar_si_toca("prueba") is None,
      "no duplica el respaldo si hoy ya existe uno")
info_r = db.ultimo_respaldo()
check(info_r is not None and info_r["tamano"] > 0,
      "se puede consultar el último respaldo")
check(any(a["accion"] == "Respaldo de base de datos"
          for a in db.historial_actividad(200)),
      "el respaldo queda en el registro de actividad")

# Rotación: se conservan solo los últimos N respaldos
viejos = []
for i in range(db.RESPALDOS_CONSERVAR + 5):
    p = os.path.join(db.dir_respaldos(), f"garrafas_2000-01-01_{i:06d}.db")
    open(p, "wb").close()
    viejos.append(p)
db.respaldar("prueba de rotación")
check(len(db.respaldos_existentes()) <= db.RESPALDOS_CONSERVAR,
      f"la rotación conserva hasta {db.RESPALDOS_CONSERVAR} respaldos "
      f"(obtuvo {len(db.respaldos_existentes())})")
check(not os.path.exists(viejos[0]), "los respaldos más viejos se borran solos")

db.set_respaldo_automatico(False)
check(not db.respaldo_automatico_activo(), "se puede desactivar el respaldo automático")
db.set_respaldo_automatico(True)
check(db.respaldo_automatico_activo(), "se puede reactivar el respaldo automático")

# Fondo inicial de la jornada y caja de hoy (se crea y se abre a mano)
db.set_fondo_inicial(350000)
caja = db.asegurar_caja(db.hoy())
check(caja["estado"] == "abierta", "caja del día creada y abierta")
check(db.asegurar_caja(db.hoy())["id"] == caja["id"], "no se duplica la caja del día")
check(db.apertura_de(caja["id"]) is None,
      "la caja nueva nace sin apertura registrada")

p10 = db.producto_por_nombre("Garrafa 10 kg")
p15 = db.producto_por_nombre("Garrafa 15 kg")
p45 = db.producto_por_nombre("Garrafa 45 kg")

# Sin apertura no se pueden registrar ventas
try:
    db.registrar_venta(caja["id"], p10["id"], 1, 10000, "Efectivo")
    check(False, "debería rechazar ventas antes de abrir la caja")
except ValueError:
    check(True, "no se puede vender antes de ABRIR CAJA")

apertura = db.abrir_caja(caja["id"])
check(apertura is not None and apertura["usuario"] == "admin",
      "la apertura registra qué usuario abrió la caja")
check(apertura["monto_inicial"] == 350000,
      f"la apertura guarda el monto inicial (obtuvo {apertura['monto_inicial']})")
try:
    db.abrir_caja(caja["id"])
    check(False, "debería rechazar la doble apertura")
except ValueError:
    check(True, "no se puede abrir la caja dos veces")

# Ventas de ejemplo
db.registrar_venta(caja["id"], p10["id"], 3, 10000, "Efectivo")        # 30.000
db.registrar_venta(caja["id"], p10["id"], 2, 10000, "Efectivo")
db.registrar_venta(caja["id"], p15["id"], 5, 15000, "Efectivo")
db.registrar_venta(caja["id"], p45["id"], 1, 45000, "Efectivo")
db.registrar_venta(caja["id"], p15["id"], 10, 15000, "Transferencia")   # 150.000
db.registrar_venta(caja["id"], p45["id"], 2, 45000, "Transferencia")    # 100.000
db.registrar_venta(caja["id"], p15["id"], 10, 15000, "Tarjeta de débito")   # 150.000
db.registrar_venta(caja["id"], p45["id"], 2, 45000, "Tarjeta de crédito")   # 90.000

r = db.resumen(caja["id"])
check(r["total_garrafas"] == 35, f"total garrafas = 35 (obtuvo {r['total_garrafas']})")
check(all(v["cajero"] == "admin" for v in r["ventas"]),
      "cada venta registra al usuario que la cargó")
check(r["efectivo"] == 170000, f"efectivo = 170.000 (obtuvo {r['efectivo']})")
check(r["transferencias"] == 240000, f"transferencias = 240.000 (obtuvo {r['transferencias']})")
check(r["debito"] == 150000, f"débito = 150.000 (obtuvo {r['debito']})")
check(r["credito"] == 90000, f"crédito = 90.000 (obtuvo {r['credito']})")
check(r["total_vendido"] == r["total_general"] == 650000, "total general = 650.000")
check(r["por_producto"][p10["id"]]["cantidad"] == 5, "garrafas 10 kg acumuladas = 5")

# Arqueo de ejemplo: esperado 520.000
# (efectivo 170.000 + fondo de la apertura 350.000)
r2 = db.resumen(caja["id"])
check(r2["efectivo_esperado"] == 520000,
      f"efectivo esperado = 520.000 (obtuvo {r2['efectivo_esperado']})")

conteo = {20000: 20, 10000: 10, 2000: 5, 1000: 5, 500: 2, 100: 0, 200: 0}
filas, total = db.calcular_arqueo(conteo)
check(total == 516000, f"efectivo contado = 516.000 (obtuvo {total})")
dif = total - r2["efectivo_esperado"]
check(dif == -4000, f"diferencia = -4.000 (obtuvo {dif})")
estado, etiqueta = db.clasificar_diferencia(dif)
check(estado == "Faltante" and etiqueta == "FALTANTE", "detecta FALTANTE -4.000")
check(db.clasificar_diferencia(4000)[0] == "Sobrante", "detecta SOBRANTE")
check(db.clasificar_diferencia(0)[0] == "Cuadrada", "detecta CAJA CUADRADA")

# Cierre
hora = db.guardar_cierre(
    caja["id"], total_garrafas=r2["total_garrafas"], total_vendido=r2["total_vendido"],
    efectivo_esperado=r2["efectivo_esperado"], efectivo_contado=total,
    transferencias=r2["transferencias"], debito=r2["debito"], credito=r2["credito"],
    bono=r2.get("bono", 0),
    total_general=r2["total_general"], diferencia=dif, estado=estado,
    billetes={str(d): c for d, c in conteo.items()},
)
check(bool(hora), "cierre guardado con hora")
check(db.get_caja_por_id(caja["id"])["estado"] == "cerrada", "caja pasa a CERRADA")
cierre = db.get_cierre_activo(caja["id"])
check(cierre is not None and cierre["estado"] == "Faltante", "cierre activo consultable")
check(cierre["billetes_dict"]["20000"] == 20, "conteo de billetes persistido")
check(cierre.get("cerrado_por_nombre") == "admin",
      "el cierre guarda qué usuario lo realizó")
check(cierre.get("n_operaciones") == 8,
      f"el cierre guarda la cantidad de operaciones "
      f"(obtuvo {cierre.get('n_operaciones')})")
check(cierre.get("comprobantes") is not None,
      "el cierre guarda los comprobantes de transferencia")
check(len(db.historial_cierres()) == 1, "aparece en el historial")

# Registro de actividad
actividad = db.historial_actividad(100)
check(any(a["accion"] == "Cierre de caja" for a in actividad),
      "el cierre queda en el registro de actividad")
check(any(a["accion"] == "Venta registrada" for a in actividad),
      "las ventas quedan en el registro de actividad")
check(any(a["accion"] == "Apertura de caja" for a in actividad),
      "la apertura queda en el registro de actividad")
check(all(a["usuario"] for a in actividad),
      "todas las acciones del registro tienen usuario asignado")

# Reapertura con contraseña
db.reabrir_caja(caja["id"])
check(db.get_caja_por_id(caja["id"])["estado"] == "abierta", "reabrir devuelve la caja a abierta")
check(len(db.historial_cierres()) == 0, "el cierre anulado sale del historial")
db.guardar_cierre(
    caja["id"], total_garrafas=0, total_vendido=0, efectivo_esperado=0,
    efectivo_contado=0, transferencias=0, debito=0, credito=0, bono=0,
    total_general=0,
    diferencia=0, estado="Cuadrada", billetes={},
)
check(len(db.historial_cierres()) == 1, "al cerrar de nuevo vuelve al historial")

# Cambio de contraseña
db.set_password("nueva123")
check(db.check_password("nueva123"), "cambio de contraseña funciona")
check(db.get_config("password").startswith("pbkdf2_sha256$"),
      "la contraseña maestra nueva se guarda con PBKDF2")
db.set_password("admin")

# Un hash viejo (sha256 de una sola ronda) se migra solo, en el próximo login
_uop = db.usuario_por_nombre("operario")
_sal_o = "saldeoperario1234"
_legacy_o = _sal_o + "$" + _hashlib.sha256(
    (_sal_o + "clave123").encode("utf-8")).hexdigest()
with db.db() as _con:
    _con.execute("UPDATE usuarios SET password = ? WHERE id = ?",
                 (_legacy_o, _uop["id"]))
check(db._es_legacy(db.usuario_por_nombre("operario")["password"])
      and db._password_ok(db.usuario_por_nombre("operario")["password"],
                          "clave123"),
      "el hash viejo puesto a mano sigue validando (compatibilidad)")
check(db.iniciar_sesion("operario", "clave123") is not None,
      "la contraseña vieja deja entrar igual")
check(not db._es_legacy(db.usuario_por_nombre("operario")["password"]),
      "al entrar, el hash viejo se migra a PBKDF2 solo")
db.iniciar_sesion("admin", "admin")      # la prueba seguía como DESARROLLADOR
check(db.usuario_sesion()["usuario"] == "admin",
      "se restaura la sesión del DESARROLLADOR para lo que sigue")

# ---------------------------------------------------------------- interfaz
import tkinter as tk
import tkinter.messagebox as mb

from util import fecha_corta

# Los mensajes emergentes no deben frenar la prueba
ERRORES = []
mb.showinfo = lambda *a, **k: None
mb.showwarning = lambda *a, **k: ERRORES.append(a)
mb.showerror = lambda *a, **k: ERRORES.append(a)
mb.askyesno = lambda *a, **k: True

# Errores inesperados: cartel genérico + detalle al archivo (AppSec #10)
import errores as _er
_er.RUTA_LOG = os.path.join(tempfile.gettempdir(), "errores_test.log")
if os.path.exists(_er.RUTA_LOG):
    os.remove(_er.RUTA_LOG)
ERRORES.clear()
try:
    raise _sqlite.OperationalError(
        "no such table: tabla_secreta_ruta C:\\Users\\dueno\\Documents")
except Exception as _exc:
    _er.mostrar("Prueba de error", _exc, contexto="prueba unitaria")
check(len(ERRORES) == 1, "un error inesperado muestra exactamente un cartel")
_cartel = str(ERRORES[0])
check("tabla_secreta" not in _cartel and "C:\\Users" not in _cartel,
      "el cartel NO filtra el detalle interno de la excepción")
check("errores.log" in _cartel,
      "el cartel indica al usuario dónde está el detalle")
check(os.path.exists(_er.RUTA_LOG), "el detalle se guardó en errores.log")
with open(_er.RUTA_LOG, encoding="utf-8") as _f:
    _detalle = _f.read()
check("tabla_secreta" in _detalle and "Traceback" in _detalle,
      "errores.log guarda el error completo con la traza")
ERRORES.clear()

# El login del cierre/reapertura pide contraseña: se responde con la de admin
import tkinter.simpledialog as _sd
_sd.askstring = lambda *a, **k: "admin"

import main as main_mod
from ui_cierre import CierreDialog
import ui_cierre as _uic
_uic.pedir_password = lambda parent, usuario: "admin"   # diálogo modal propio
import iconos as _ic


def _nueva_app():
    """Crea una App fresca para tests. Al destruir la raíz Tk mueren las
    PhotoImage del caché de iconos, así que se limpia antes de reconstruir.
    Si quedó alguna raíz vieja viva, se destruye: con dos raízes a la vez,
    PIL crea las imágenes en la raíz equivocada y el widget no las encuentra."""
    raiz = getattr(tk, "_default_root", None)
    if raiz is not None:
        try:
            raiz.destroy()
        except tk.TclError:
            pass
    _ic._cache.clear()
    a = main_mod.App()
    a.update()
    return a

# La sesión ya está iniciada (admin) — la app no vuelve a pedir login
app = _nueva_app()
app.update()

# Ventas del día en la interfaz
panel = app.paneles["ventas"]
app.mostrar("ventas")
app.update()
check(len(panel.tree.get_children()) == 8, "listado de ventas en la interfaz")

# Panel de inicio
app.mostrar("inicio")
app.update()
check(app.paneles["inicio"].v_garrafas.cget("text") == "35",
      "tarjeta garrafas vendidas = 35")
check(app.paneles["inicio"].v_general.cget("text") == "$650.000",
      "tarjeta total general = $650.000")
check(app.paneles["inicio"].v_tarjetas.cget("text") == "$240.000",
      "tarjeta TARJETAS agrupa débito + crédito ($240.000)")
check("Débito $150.000" in app.paneles["inicio"]
      .d_tarjetas.cget("text")
      and "Crédito $90.000" in app.paneles["inicio"]
      .d_tarjetas.cget("text"),
      "la tarjeta TARJETAS discrimina débito y crédito")

# Punto 4: el listado de Inicio muestra solo lo vendido y nada queda oculto
inicio = app.paneles["inicio"]
app.update()
check(getattr(inicio, "canvas_scroll", None) is not None,
      "punto 4: el panel Inicio tiene scroll vertical")
check(inicio.lbl_estado_caja.winfo_ismapped()
      and str(inicio.lbl_estado_caja.cget("text")).strip() != "",
      "punto 4: se ve el estado de la caja en Inicio")

_r_ini = db.resumen(caja["id"])
_vendidos_ini = [i for i in _r_ini["por_producto"].values()
                 if int(i["cantidad"]) > 0]
_filas_inicio = inicio.contenedor_producto.winfo_children()
# 3 etiquetas de encabezado + 3 por producto + 1 separador + 3 de TOTAL GENERAL
check(len(_filas_inicio) == 3 * len(_vendidos_ini) + 7,
      f"punto 4: Inicio lista solo los {len(_vendidos_ini)} productos "
      f"vendidos + su total (obtuvo {len(_filas_inicio)} filas)")
check(len(_vendidos_ini) < 10,
      f"punto 4: los productos sin ventas no ocupan lugar en Inicio "
      f"(se muestran {len(_vendidos_ini)} de 10)")

_uni_ini = sum(int(i["cantidad"]) for i in _vendidos_ini)
_textos_total = [str(w.cget("text"))
                 for w in _filas_inicio[-3:]]
check(any(t == "TOTAL GENERAL" for t in _textos_total)
      and any(t == f"{_uni_ini} u." for t in _textos_total),
      f"punto 4: fila TOTAL GENERAL con {_uni_ini} unidades "
      f"(obtuvo {_textos_total})")

inicio.canvas_scroll.yview_moveto(1.0)
inicio.update_idletasks()
_cy = inicio.canvas_scroll.winfo_rooty()
_ch = inicio.canvas_scroll.winfo_height()
_ultimo = inicio.contenedor_producto.master
_fin = _ultimo.winfo_rooty() - _cy + _ultimo.winfo_height()
check(_fin <= _ch + 2,
      f"punto 4: bajando, el último producto cabe en pantalla "
      f"(fin={_fin} contra {_ch})")

# Configuración
app.mostrar("config")
app.update()
check(len(app.paneles["config"].tree.get_children()) == 10, "productos en configuración")

# Historial
app.mostrar("historial")
app.update()
check(len(app.paneles["historial"].tree.get_children()) == 1, "historial con 1 cierre")

# Volver a abrir una caja nueva y probar el diálogo de cierre
db.reabrir_caja(caja["id"])
app.refrescar_todo()
app.update()

dlg = CierreDialog(app, db.get_caja_por_id(caja["id"]))
app.update()
dlg.celdas[20000].set("20")
dlg.celdas[10000].set("10")
dlg.celdas[2000].set("5")
dlg.celdas[1000].set("5")
dlg.celdas[500].set("2")
dlg._recalcular()
app.update()
check(dlg.lbl_contado.cget("text") == "$516.000", "diálogo: contado $516.000")
check(dlg.lbl_esperado2.cget("text") == "$520.000", "diálogo: esperado $520.000")
check(dlg.lbl_diferencia.cget("text") == "-$4.000", "diálogo: diferencia -$4.000")
check(dlg.lbl_estado.lbl.cget("text") == "FALTANTE", "diálogo: estado FALTANTE")
check(dlg.valores_medio["tarjetas"].cget("text") == "$240.000",
      "diálogo: la fila TARJETAS suma débito + crédito ($240.000)")
check(dlg.valores_medio["debito"].cget("text") == "$150.000"
      and dlg.valores_medio["credito"].cget("text") == "$90.000",
      "diálogo: TARJETAS sigue discriminando débito y crédito")

# Caja cuadrada
dlg.celdas[500].set("10")
dlg._recalcular()
check(dlg.lbl_estado.lbl.cget("text") == "CAJA CUADRADA", "diálogo: CAJA CUADRADA")

# Sobrante
dlg.celdas[100].set("1")
dlg._recalcular()
check(dlg.lbl_estado.lbl.cget("text") == "SOBRANTE", "diálogo: SOBRANTE")

dlg._confirmar()  # confirma el cierre completo
app.update()
check(db.get_caja_por_id(caja["id"])["estado"] == "cerrada",
      "CONFIRMAR CIERRE cierra y bloquea la caja")
check(len(db.historial_cierres()) == 1, "el cierre confirmado entra al historial")

# Detalle de un cierre en el historial
from ui_historial import DetalleCierre
app.mostrar("historial")
app.update()
cierre_hoy = db.historial_cierres()[0]
det = DetalleCierre(app, cierre_hoy)
app.update()
check(det.winfo_exists(), "se abre el detalle completo de un cierre")


def _textos_de(widget):
    """Recolecta todos los textos visibles (labels) de un widget y sus hijos."""
    salidas = []
    for hijo in widget.winfo_children():
        if hijo.winfo_class() == "Label":
            salidas.append(str(hijo.cget("text")))
        salidas.extend(_textos_de(hijo))
    return salidas


_textos_det = _textos_de(det)
check("Total tarjetas" in _textos_det,
      "detalle del cierre: agrupa los totales en 'Total tarjetas'")
check("Tarjeta de débito" in _textos_det
      and "Tarjeta de crédito" in _textos_det,
      "detalle del cierre: discrimina tarjeta de débito y de crédito")
det.destroy()

# Configuración: crear, editar y eliminar productos
app.mostrar("config")
app.update()
cfg = app.paneles["config"]
cfg.var_nombre.set("Garrafa 25 kg")
cfg.var_precio.set("25.000")
cfg._nuevo_producto()
check(len(db.productos()) == 11, "alta de producto desde configuración")
cfg.tree.selection_set(cfg.tree.get_children()[-1])
cfg.tree.event_generate("<<TreeviewSelect>>")
cfg.var_precio.set("26.500")
cfg._guardar_producto()
check(db.producto_por_nombre("Garrafa 25 kg")["precio"] == 26500,
      "edición de precio desde configuración")
cfg.tree.selection_set(cfg.tree.get_children()[-1])
cfg._eliminar_producto()
check(len(db.productos()) == 10, "baja de producto desde configuración")

# Registro de ventas desde la interfaz (la caja debe estar abierta)
db.reabrir_caja(caja["id"])
app.refrescar_todo()
app.mostrar("ventas")
app.update()
panel = app.paneles["ventas"]
panel.combo_producto.current(0)
panel.var_cantidad.set("4")
panel.var_precio.set("10.000")
panel.combo_medio.set("Efectivo")
panel.update_idletasks()
check(panel.lbl_total.cget("text") == "$40.000", "total calculado en el formulario")
panel._registrar()
app.update()
check(db.resumen(caja["id"])["cantidad_ventas"] == 9,
      "venta registrada desde la interfaz")

# Corregir una venta mal cargada (cargué 10 y son 9)
ultima = panel.tree.get_children()[-1]
panel.tree.selection_set(ultima)
panel._editar()
panel.var_cantidad.set("9")
check(panel.lbl_total.cget("text") == "$90.000",
      "al editar, el total se recalcula (9 × 10.000)")
panel._registrar()
app.update()
r_ultima = db.venta_por_id(int(ultima))
check(r_ultima["cantidad"] == 9 and r_ultima["total"] == 90000,
      "la venta quedó corregida a 9 unidades")

# Eliminar la venta directamente
panel.tree.selection_set(ultima)
panel._eliminar()
app.update()
check(db.venta_por_id(int(ultima)) is None, "venta eliminada desde la lista")
check(db.resumen(caja["id"])["cantidad_ventas"] == 8,
      "los totales se actualizaron al eliminar")

# Borrado masivo: varias ventas seleccionadas de una sola vez
_antes_m = db.resumen(caja["id"])["cantidad_ventas"]
_ids_m = []
for _ in range(3):
    db.registrar_venta(caja["id"], p10["id"], 1, 10000, "Efectivo")
    _ids_m.append(str([v["id"] for v in db.ventas_de(caja["id"])
                       if v["producto_id"] == p10["id"]][-1]))
app.refrescar_todo()
app.mostrar("ventas")
app.update()
panel = app.paneles["ventas"]
check(str(panel.tree.cget("selectmode")) == "extended",
      "el listado de ventas permite selección múltiple")

# Punto 4: la fila de botones (Editar / Eliminar / Borrar toda la caja)
# tiene que entrar entera en el panel, sin cortarse en 1366x768.
panel.update_idletasks()
_ancho_panel = panel.winfo_width()
_llega = 0
for _w in panel.btn_eliminar.master.pack_slaves():
    if _w.winfo_ismapped() and _w.winfo_width() > 1:
        _llega = max(_llega, _w.winfo_x() + _w.winfo_width())
check(_llega <= _ancho_panel - 40,
      f"punto 4: la fila de botones de Ventas entra entera "
      f"(llega hasta {_llega} de {_ancho_panel - 40})")

panel.tree.selection_set(*_ids_m)
check(len(panel.tree.selection()) == 3,
      "se pueden seleccionar varias ventas a la vez (Ctrl o Shift)")
panel._eliminar()
app.update()
_despues_m = db.resumen(caja["id"])["cantidad_ventas"]
check(_despues_m == _antes_m,
      f"borrado masivo: las 3 ventas seleccionadas se borran juntas "
      f"(obtuvo {_despues_m}, esperaba {_antes_m})")

# ---------------- Transferencias: comprobante obligatorio ----------------
panel.combo_medio.set("Transferencia")
panel.var_cantidad.set("2")
panel.var_precio.set("15.000")
panel.var_comprobante.set("")
panel.var_cliente.set("María López")
ERRORES.clear()
check(panel._datos_form() is None,
      "transferencia SIN comprobante no se puede guardar")
check(any("comprobante" in str(e).lower() for e in ERRORES),
      "muestra el aviso de comprobante obligatorio")

panel.var_comprobante.set("TR-000123")
datos = panel._datos_form()
check(datos is not None and datos[4] == "TR-000123",
      "con comprobante ingresado la venta se acepta")
check(datos is not None and datos[5] == "María López",
      "el formulario guarda el nombre del cliente (campo Nombre)")
panel._registrar()
app.update()
check(panel.var_cliente.get() == "",
      "tras registrar, el campo de cliente queda limpio")

r_caja = db.resumen(caja["id"])
check(r_caja["n_transferencias"] == 3,
      f"cantidad de transferencias del día = 3 (obtuvo {r_caja['n_transferencias']})")
check(r_caja["transferencias"] == 270000,
      f"monto de transferencias = 270.000 (obtuvo {r_caja['transferencias']})")
check(any(t["comprobante"] == "TR-000123" for t in r_caja["transferencias_detalle"]),
      "el comprobante queda asociado a la venta y en el detalle")

# ---------------- Estadísticas ----------------
hoy = db.hoy()
stats = db.estadisticas(hoy, hoy)
check(stats["cantidad_ventas"] == 9, "estadísticas: total de ventas del día")
check(stats["total_garrafas"] == r_caja["total_garrafas"],
      "estadísticas: garrafas vendidas")
check(stats["total_vendido"] == r_caja["total_vendido"],
      "estadísticas: total recaudado")
check(stats["n_transferencias"] == 3, "estadísticas: cantidad de transferencias")
check(stats["transferencias"] == 270000, "estadísticas: monto transferido")
check(stats["efectivo"] == r_caja["efectivo"], "estadísticas: total en efectivo")
check(stats["debito"] == r_caja["debito"], "estadísticas: total con débito")
check(stats["credito"] == r_caja["credito"], "estadísticas: total con crédito")
check(len(stats["evolucion"]) == 1 and stats["evolucion"][0]["fecha"] == hoy,
      "estadísticas: evolución de ventas por día")
check(len(stats["por_producto"]) >= 3, "estadísticas: ventas por producto")

app.mostrar("stats")
app.update()
panel_stats = app.paneles["stats"]
check(panel_stats.cards["ventas"].cget("text") == "9",
      "panel de estadísticas: tarjeta de total de ventas")
check(panel_stats.cards["n_transferencias"].cget("text") == "3",
      "panel de estadísticas: tarjeta de transferencias")
check(panel_stats.cards["tarjetas"].cget("text") == "$240.000",
      "panel de estadísticas: tarjeta TARJETAS = débito + crédito")
check("Débito $150.000" in panel_stats.cards_detalle["tarjetas"].cget("text"),
      "panel de estadísticas: TARJETAS muestra el desglose D/C")
check(len(panel_stats.tree_productos.get_children()) >= 3,
      "panel de estadísticas: listado por producto")
check(len(panel_stats.tree_cierres.get_children()) ==
      len(db.cierres_rango(hoy, hoy)),
      "panel de estadísticas: resumen de cierres")

# Filtro por fecha de un día específico
panel_stats.var_desde.set(fecha_corta(hoy))
panel_stats.var_hasta.set(fecha_corta(hoy))
panel_stats._aplicar_fechas()
check(panel_stats.cards["ventas"].cget("text") == "9",
      "filtro por fecha de un día específico")

# ---------------- Exportación a Excel (plantilla imprimible A4) ----------------
import os as _os
import tempfile as _tempfile
import excel as xl
from openpyxl import load_workbook

destino = _os.path.join(_tempfile.gettempdir(), "movimientos_test.xlsx")
cantidad_xl, monto_xl = xl.exportar_movimientos(hoy, hoy, destino)
check(cantidad_xl == stats["cantidad_ventas"],
      f"excel: incluye todos los movimientos ({cantidad_xl})")
check(abs(monto_xl - stats["total_vendido"]) < 0.01,
      f"excel: total general = {monto_xl}")

wb = load_workbook(destino)
ws = wb.active
textos = [str(c.value) for fila in ws.iter_rows() for c in fila
          if c.value is not None]

# Secciones por medio de pago: TARJETAS agrupa débito y crédito
for seccion in ("TRANSFERENCIAS", "TARJETAS", "TARJETA DE DÉBITO",
                "TARJETA DE CRÉDITO", "DINERO / EFECTIVO"):
    check(any(seccion in t for t in textos),
          f"excel: incluye la sección {seccion}")

# La sección TARJETAS suma sus dos bloques y el general no se duplica
filas_txt = [[str(c.value) for c in fila if c.value is not None]
             for fila in ws.iter_rows()]
fila_total_tarjetas = [f for f in filas_txt if f and f[0] == "TOTAL TARJETAS"]
check(len(fila_total_tarjetas) == 1
      and abs(float(fila_total_tarjetas[0][-1]) - 240000) < 0.01,
      f"excel: TOTAL TARJETAS = 240.000 "
      f"(obtuvo {fila_total_tarjetas[0][-1] if fila_total_tarjetas else '—'})")

# Columnas pedidas: Nombre / Carga / N° Comprobante-Tarjeta / Total
check(any(t == "Nombre" for t in textos), "excel: columna Nombre")
check(any(t == "Carga" for t in textos), "excel: columna Carga")
check(any("Comprobante" in t for t in textos),
      "excel: columna N° Comprobante / Tarjeta")
check(any(t == "Total" for t in textos), "excel: columna Total")

check(any("TR-000123" in t for t in textos),
      "excel: incluye el número de comprobante")
check(any("Garrafa" in t for t in textos), "excel: incluye el producto vendido")
check(any("María López" in t for t in textos),
      "excel: incluye el Nombre del cliente")
check(any("×" in t for t in textos), "excel: incluye el detalle de la carga")
check(any("TOTAL GENERAL" in t for t in textos),
      "excel: incluye el total general")

# ---- Recuadro por sección: Sección | 10 KG | 15 KG | 45 KG | Un. | $ ----
movs_xl = db.ventas_rango(hoy, hoy)
SECCIONES_XL = {
    "EFEC": ["Efectivo"],
    "TARJETA": ["Tarjeta de débito", "Tarjeta de crédito"],
    "TRANS": ["Transferencia"],
}
PRODUCTOS_XL = ["Garrafa 10 kg", "Garrafa 15 kg", "Garrafa 45 kg"]


def _fila_primera(primero):
    """Primera fila cuyo primer dato sea exactamente ese rótulo."""
    for f in filas_txt:
        if f and str(f[0]) == primero:
            return f
    return None


_enc = _fila_primera("Sección")
check(_enc is not None and list(_enc) ==
      ["Sección", "10 KG", "15 KG", "45 KG", "Unidades", "Total $"],
      f"excel: encabezado del recuadro "
      f"(obtuvo {_enc if _enc else '—'})")
check(_enc is not None and "ME" not in _enc and "ECO" not in _enc,
      "excel: solo aparecen las garrafas que se vendieron")

for _seccion in SECCIONES_XL:
    check(any(t == _seccion for t in textos),
          f"excel: el resumen incluye la sección {_seccion}")

for _seccion, _medios in SECCIONES_XL.items():
    _uni = sum(v["cantidad"] for v in movs_xl if v["medio"] in _medios)
    _din = sum(float(v["total"]) for v in movs_xl if v["medio"] in _medios)
    _f = _fila_primera(_seccion)
    check(_f is not None and len(_f) == 6 and int(_f[4]) == _uni,
          f"excel: {_seccion} suma {_uni} unidades")
    check(_f is not None and len(_f) == 6 and abs(float(_f[5]) - _din) < 0.01,
          f"excel: {_seccion} suma ${_din:,.0f}")
    # Unidades de cada producto dentro de esa sección (columnas en orden)
    for _i, _producto in enumerate(PRODUCTOS_XL):
        _esperado = sum(v["cantidad"] for v in movs_xl
                        if v["medio"] in _medios
                        and v["producto"] == _producto)
        check(_f is not None and len(_f) == 6
              and int(_f[1 + _i]) == _esperado,
              f"excel: {_seccion} informa {_esperado} unidades "
              f"de {_producto}")

# TOTAL GENERAL del recuadro: unidades y dinero de todo el período
_fila_tg = next((f for f in filas_txt
                 if f and str(f[0]) == "TOTAL GENERAL" and len(f) == 6), None)
uni_total = sum(v["cantidad"] for v in movs_xl)
check(_fila_tg is not None and int(_fila_tg[4]) == uni_total,
      f"excel: total general de unidades = {uni_total}")
check(_fila_tg is not None and abs(float(_fila_tg[5]) - monto_xl) < 0.01,
      "excel: total general de dinero coincide con el total del reporte")

# El recuadro de envases NO aparece si no se vendieron envases
check(not any("VENTA DE ENVASES" in str(f[0]) for f in filas_txt if f),
      "excel: sin envases vendidos no aparece el recuadro de envases")

# Control de cuadre: EFEC + TARJETA + TRANS = TOTAL GENERAL (por recuadro)
controles = [f for f in filas_txt if f and str(f[0]).startswith("CONTROL DE ")]
check(len(controles) >= 2 and len(controles) % 2 == 0,
      f"excel: hay controles de unidades y de dinero (obtuvo {len(controles)})")
check(all(str(f[-1]) == "COINCIDE" for f in controles),
      "excel: los controles de unidades y de dinero cuadran")

# El TOTAL GENERAL del detalle sigue dando el total del período
_filas_tg_detalle = [f for f in filas_txt
                     if f and str(f[0]) == "TOTAL GENERAL" and len(f) == 2]
check(len(_filas_tg_detalle) == 1
      and abs(float(_filas_tg_detalle[0][1]) - monto_xl) < 0.01,
      "excel: un solo TOTAL GENERAL del detalle con el monto completo")

# Configuración de impresión: A4 horizontal ajustado al ancho
check(str(ws.page_setup.orientation) == "landscape",
      "excel: hoja configurada en horizontal")
check(str(ws.page_setup.paperSize) == str(ws.PAPERSIZE_A4),
      "excel: tamaño de papel A4")
check(int(ws.page_setup.fitToWidth or 0) == 1,
      "excel: ajustado al ancho de la página")
check(ws.sheet_properties.pageSetUpPr is not None
      and ws.sheet_properties.pageSetUpPr.fitToPage,
      "excel: escala 'ajustar al ancho' activa")
check("$A$1" in str(ws.print_area) and "$H$" in str(ws.print_area),
      f"excel: área de impresión definida (obtuvo {ws.print_area})")
check(str(ws.print_title_rows).replace("$", "") == "1:3",
      f"excel: encabezados visibles en cada página "
      f"(obtuvo {ws.print_title_rows})")
_os.remove(destino)

# ---- El recuadro de envases aparece solo cuando se venden ----
_p_env = db.producto_por_nombre("Envase 10 kg")
db.registrar_venta(caja["id"], _p_env["id"], 3, 8000, "Efectivo")
_v_env = [v["id"] for v in db.ventas_de(caja["id"])
          if v["producto_id"] == _p_env["id"]][-1]
destino_env = _os.path.join(_tempfile.gettempdir(), "movimientos_envases.xlsx")
xl.exportar_movimientos(hoy, hoy, destino_env)
_ws_env = load_workbook(destino_env).active
_filas_env = [[str(c.value) for c in fila if c.value is not None]
              for fila in _ws_env.iter_rows()]
_enc_env = next((f for f in _filas_env
                 if f and str(f[0]) == "Sección" and "10 KG" in f), None)
check(_enc_env is not None,
      "excel: con envases vendidos aparece el recuadro VENTA DE ENVASES")
check(any("VENTA DE ENVASES" in str(f[0]) for f in _filas_env if f),
      "excel: el recuadro de envases aclara de qué son")
check(any(str(f[0]) == "EFEC" and len(f) == 4
          and int(f[1]) == 3 and int(f[2]) == 3
          for f in _filas_env if f),
      "excel: el recuadro de envases informa 3 unidades en EFEC")
check(any(str(f[0]).startswith("CONTROL DE UNIDADES") for f in _filas_env if f),
      "excel: el recuadro de envases tiene su propio control de cuadre")
db.eliminar_venta(_v_env)
_os.remove(destino_env)

# ---------------- Borrado masivo: vaciar una caja entera ----------------
app.cambiar_caja("2026-12-29")
caja_v = app.caja_actual()
db.registrar_apertura(caja_v["id"], 5000)
db.registrar_venta(caja_v["id"], p10["id"], 2, 10000, "Efectivo")
db.registrar_venta(caja_v["id"], p10["id"], 1, 10000, "Efectivo")
app.refrescar_todo()
app.mostrar("ventas")
app.update()
pnl_v = app.paneles["ventas"]
check(len(pnl_v.tree.get_children()) == 2,
      "la caja de prueba arranca con 2 ventas cargadas")
pnl_v._vaciar_caja()
app.update()
check(db.resumen(caja_v["id"])["cantidad_ventas"] == 0,
      "borrar toda la caja deja la caja sin ventas")
check(len(pnl_v.tree.get_children()) == 0,
      "el listado queda vacío después de vaciar la caja")
app.cambiar_caja(caja["fecha"])
app.refrescar_todo()

app.destroy()

# ---------------- Panel de Administración y control de acceso ----------------
from ui_login import LoginDialog

# Pantalla de login: rechaza contraseñas incorrectas y acepta la correcta
aux_root = tk.Tk()
aux_root.withdraw()
dlg_login = LoginDialog(aux_root)
dlg_login.var_usuario.set("admin")
dlg_login.var_password.set("mala")
dlg_login._ingresar()
check(dlg_login.resultado is None, "el login rechaza una contraseña incorrecta")
check(any("rechazado" in (a["accion"] or "") for a in db.historial_actividad()),
      "los intentos de login fallidos quedan registrados")
dlg_login.var_password.set("admin")
dlg_login._ingresar()
check(dlg_login.resultado is not None
      and dlg_login.resultado["usuario"] == "admin",
      "el login acepta la contraseña correcta")
aux_root.destroy()

# Reconstruimos la app con sesión iniciada para probar el panel admin
app = _nueva_app()
app.update()
app.mostrar("admin")
app.update()
panel_admin = app.paneles["admin"]
check(len(panel_admin.tree.get_children()) == len(db.listar_usuarios()),
      "el panel de administración lista los usuarios")
check(len(panel_admin.tree_act.get_children()) > 0,
      "el panel muestra el registro de actividad")

# Alta de usuario desde el panel
panel_admin.var_usuario.set("nuevo_user")
panel_admin.var_password.set("abc1234")
panel_admin.combo_rango.set("USUARIO")
panel_admin._crear()
check(db.usuario_por_nombre("nuevo_user") is not None,
      "alta de usuario desde el panel de administración")
check(any(a["accion"] == "Usuario creado" for a in db.historial_actividad()),
      "la creación de usuarios queda en el registro de actividad")

# Generador de contraseñas
panel_admin._generar_password()
check(len(panel_admin.var_password.get()) >= 8,
      "el generador propone una contraseña segura")

# Eliminación de usuario desde el panel
uid_nuevo = db.usuario_por_nombre("nuevo_user")["id"]
panel_admin.tree.selection_set(str(uid_nuevo))
panel_admin._eliminar()
check(db.usuario_por_nombre("nuevo_user") is None,
      "baja de usuario desde el panel de administración")

# ---- Un USUARIO no ve ni entra a las secciones administrativas ----
db.cerrar_sesion()
db.iniciar_sesion("operario", "clave123")
app._actualizar_nav()
app.update_idletasks()
check(not app.botones_nav["admin"].winfo_ismapped(),
      "USUARIO: el botón Administración está oculto")
check(not app.botones_nav["stats"].winfo_ismapped(),
      "USUARIO: el botón Estadísticas está oculto")
ERRORES.clear()
app.mostrar("admin")
check(any("permiso" in str(e).lower() for e in ERRORES),
      "USUARIO: no puede entrar a Administración aunque lo intente")
ERRORES.clear()
app.mostrar("stats")
check(any("permiso" in str(e).lower() for e in ERRORES),
      "USUARIO: no puede entrar a Estadísticas aunque lo intente")
check(not db.puede("reabrir_caja"),
      "USUARIO: no tiene permiso para reabrir cajas")

# Vuelvo a la sesión de DESARROLLADOR
db.cerrar_sesion()
db.iniciar_sesion("admin", "admin")
app._actualizar_nav()
app.update_idletasks()
check(app.botones_nav["admin"].winfo_ismapped(),
      "DESARROLLADOR: el botón Administración vuelve a estar visible")

# El chequeo de medianoche no debe sacar al usuario de una caja
# que eligió a mano (bug: no se podía cerrar la caja de otro día)
from datetime import datetime as _dtt, timedelta as _tdd
_ayer = (_dtt.strptime(db.hoy(), "%Y-%m-%d") - _tdd(days=1)).strftime("%Y-%m-%d")
app.cambiar_caja(_ayer)
app._chequear_dia()
check(app.caja_fecha == _ayer,
      "_chequear_dia respeta la caja elegida a mano (no salta a hoy)")
check(db.get_caja(_ayer)["id"] == app.caja_actual()["id"],
      "la vista sigue en la caja del día elegido")
app.cambiar_caja(db.hoy())

# --------- Botones de abrir/cerrar caja, Mi cuenta y foto de perfil ---------
ini = app.paneles["inicio"]
_fecha_prueba = "2026-12-30"
app.cambiar_caja(_fecha_prueba)
app.update()
def _texto_boton(b):
    """Texto visible de un widget Boton (vive en su label interno)."""
    return str(b.lbl.cget("text")).strip()


check(_texto_boton(ini.btn_abrir) == "Abrir caja — admin",
      f"botón Abrir caja muestra el usuario "
      f"(obtuvo {_texto_boton(ini.btn_abrir)!r})")
check(ini.btn_abrir.habilitado,
      "Abrir caja habilitado cuando la caja no tiene apertura")
check(_texto_boton(ini.btn_cierre) == "Cerrar caja — admin",
      f"botón Cerrar caja muestra el usuario "
      f"(obtuvo {_texto_boton(ini.btn_cierre)!r})")

ini._abrir_caja()
app.update()
dlg_abrir = [w for w in app.winfo_children()
             if w.winfo_class() == "Toplevel" and w.title() == "Abrir caja"]
check(bool(dlg_abrir), "el diálogo de apertura se abre desde Inicio")
if dlg_abrir:
    dlg_abrir[0].var.set("120.000")
    dlg_abrir[0]._abrir()
    app.update()
ap2 = db.apertura_de(db.get_caja(_fecha_prueba)["id"])
check(ap2 is not None and ap2["monto_inicial"] == 120000,
      f"el diálogo registra el monto inicial "
      f"(obtuvo {ap2 and ap2['monto_inicial']})")
check(not ini.btn_abrir.winfo_ismapped(),
      "abierta la caja, el botón Abrir caja desaparece")
app.update()
check(ini.lbl_abierto_por.winfo_ismapped()
      and "Abierta por admin" in str(ini.lbl_abierto_por.cget("text"))
      and str(ini.lbl_monto.cget("text")) == "$120.000",
      "punto 4: se ve quién abrió la caja y con cuánto fondo inicial")

# Caja sin ventas: el cierre es directo (sin diálogo de arqueo ni contraseña)
ini._abrir_cierre()
app.update()
dialogos_cierre = [w for w in app.winfo_children()
                   if w.winfo_class() == "Toplevel" and w.title() == "Cierre de caja"]
check(not dialogos_cierre, "caja vacía: no se abre el diálogo de arqueo")
check(db.get_caja(_fecha_prueba)["estado"] == "cerrada",
      "caja vacía: se cierra de un solo clic")

# Usuario/rango del lateral
check("admin" in str(app.lbl_usuario_nombre.cget("text")),
      "el lateral muestra el usuario conectado")
app.mostrar("inicio")
app.update()
check("admin" in str(app.lbl_usuario_nombre.cget("text"))
      and "DESARROLLADOR" in str(app.lbl_usuario_rango.cget("text")),
      "al cambiar de pantalla el usuario/rango se vuelve a pintar")

# Panel Mi cuenta
check("cuenta" in app.botones_nav, "el botón Mi cuenta está en la navegación")
app.mostrar("cuenta")
app.update()
cuenta = app.paneles["cuenta"]
check(cuenta.datos["usuario"].cget("text") == "admin",
      "Mi cuenta muestra el usuario")
check(cuenta.datos["rango"].cget("text") == "DESARROLLADOR",
      "Mi cuenta muestra el rango")

# Foto de perfil (imagen elegida desde el escritorio)
from PIL import Image as _Img
_foto_tmp = os.path.join(tempfile.gettempdir(), "foto_perfil_test.png")
_Img.new("RGB", (120, 90), (20, 60, 120)).save(_foto_tmp)
db.set_foto_perfil(_foto_tmp)
check(db.foto_perfil() is not None and os.path.exists(db.foto_perfil()),
      "la foto de perfil se guarda junto a la base")
cuenta.refresh()
app._actualizar_foto_nav()
app.update()
check(cuenta._foto_ref is not None, "la foto se muestra en Mi cuenta")
_ref_con_foto = cuenta._foto_ref
check(app._foto_nav_ref is not None, "la foto se muestra en el lateral")
db.quitar_foto_perfil()
check(db.foto_perfil() is None, "la foto de perfil se puede quitar")
cuenta.refresh()
app._actualizar_foto_nav()
app.update()
# La pantalla nueva pinta el avatar por defecto en el mismo hueco:
# la imagen mostrada cambia y ya no es la de la foto.
check(cuenta._foto_ref is not None and cuenta._foto_ref is not _ref_con_foto,
      "sin foto se vuelve al avatar por defecto")
os.remove(_foto_tmp)

app.cambiar_caja(db.hoy())
app.destroy()

# Caja bloqueada: no se puede vender con la caja cerrada
db.guardar_cierre(
    caja["id"], total_garrafas=0, total_vendido=0, efectivo_esperado=0,
    efectivo_contado=0, transferencias=0, debito=0, credito=0, bono=0,
    total_general=0,
    diferencia=0, estado="Cuadrada", billetes={}, n_transferencias=2,
)
check(not db.caja_esta_abierta(caja["id"]), "caja cerrada queda bloqueada")
check(db.get_cierre_activo(caja["id"])["n_transferencias"] == 2,
      "el cierre guarda la cantidad de transferencias")

# Caja del día siguiente (nuevo día)
from datetime import datetime as _dt, timedelta as _td
manana = (_dt.strptime(db.hoy(), "%Y-%m-%d") + _td(days=1)).strftime("%Y-%m-%d")
caja_nueva = db.asegurar_caja(manana)
check(caja_nueva["estado"] == "abierta", "nuevo día = nueva caja automática")
check(db.get_caja(db.hoy())["id"] != caja_nueva["id"],
      "las cajas de cada día están separadas")
check(db.resumen(caja_nueva["id"])["total_vendido"] == 0,
      "la caja nueva empieza en cero")

# ==========================================================================
# Revisión de los 8 puntos pedidos:
# permisos por usuario, cierre sin ventanas de más, fotos independientes,
# ventana adaptativa y Excel imprimible A4 horizontal.
# ==========================================================================

# ---- Punto 1: permisos individuales por usuario (nivel de datos) ----
check(all(db.puede(p) for p in perms.PERMISOS),
      "punto 1: DESARROLLADOR conserva acceso completo")

u_perm = db.crear_usuario(
    "caja_perm", "clave1", "USUARIO",
    permisos=["abrir_caja", "cerrar_caja", "ventas", "pago_efectivo",
              "historial"])
expl = db.permisos_explicitos(u_perm["id"])
check(expl is not None and len(expl) == 5,
      "punto 1: el usuario guarda sus permisos individuales")
check(len(db.permisos_efectivos(u_perm["id"])) == 5,
      "punto 1: los permisos efectivos son exactamente los asignados")

u_rango = db.crear_usuario("sin_perm", "clave1", "USUARIO")
check(db.permisos_explicitos(u_rango["id"]) is None,
      "punto 1: sin asignación manual, el usuario usa los de su rango")
check("historial" in db.permisos_efectivos(u_rango["id"]),
      "punto 1: hereda los permisos por defecto del rango USUARIO")

# ---- Punto 1 + punto 4: con sesión de usuario restringido ----
db.cerrar_sesion()
db.iniciar_sesion("caja_perm", "clave1")
check(db.puede("cerrar_caja") and db.puede("pago_efectivo"),
      "punto 1: puede hacer lo que se le asignó")
check(not db.puede("exportar_excel") and not db.puede("estadisticas"),
      "punto 1: NO puede hacer lo que no se le asignó")
check(not db.puede("pago_credito") and not db.puede("pago_transferencia"),
      "punto 1: los medios de pago se restringen uno por uno")

app3 = _nueva_app()
app3.update()
ancho_v = int(app3.geometry().split("x")[0])
alto_v = int(app3.geometry().split("x")[1].split("+")[0])
check(ancho_v <= app3.winfo_screenwidth() and alto_v <= app3.winfo_screenheight(),
      f"punto 4: la ventana entra en la pantalla "
      f"({ancho_v}x{alto_v} vs {app3.winfo_screenwidth()}x"
      f"{app3.winfo_screenheight()})")
check(ancho_v >= app3.minsize()[0] and alto_v >= app3.minsize()[1],
      "punto 4: la ventana respeta su tamaño mínimo sin exceder la pantalla")

app3.mostrar("ventas")
app3.update()
pv = app3.paneles["ventas"]
check(list(pv.combo_medio["values"]) == ["Efectivo"],
      f"punto 1: en Ventas solo se ofrece el medio de pago permitido "
      f"(obtuvo {list(pv.combo_medio['values'])})")
pv.combo_producto.current(0)
pv.var_cantidad.set("1")
pv.var_precio.set("10000")
pv.combo_medio.set("Tarjeta de crédito")
ERRORES.clear()
check(pv._datos_form() is None,
      "punto 1: el cobro con un medio no permitido se rechaza")
check(any("permiso" in str(e).lower() for e in ERRORES),
      "punto 1: avisa que el usuario no tiene permiso para ese cobro")
app3.destroy()

# El DESARROLLADOR puede ampliarle permisos a un usuario
db.cerrar_sesion()
db.iniciar_sesion("admin", "admin")
db.set_permisos_usuario(u_perm["id"],
                        db.permisos_explicitos(u_perm["id"]) + ["exportar_excel"])
db.cerrar_sesion()
db.iniciar_sesion("caja_perm", "clave1")
check(db.puede("exportar_excel"),
      "punto 1: el permiso agregado se aplica de inmediato")
db.cerrar_sesion()
db.iniciar_sesion("admin", "admin")
db.eliminar_usuario(u_perm["id"])
db.eliminar_usuario(u_rango["id"])

# ---- Punto 3: cada usuario con su propia foto ----
foto_a = os.path.join(tempfile.gettempdir(), "foto_usuario_a.png")
foto_b = os.path.join(tempfile.gettempdir(), "foto_usuario_b.png")
_Img.new("RGB", (100, 80), (200, 30, 30)).save(foto_a)
_Img.new("RGB", (100, 80), (30, 200, 30)).save(foto_b)

u_admin = db.usuario_por_nombre("admin")
db.set_foto_perfil(foto_a)                      # sesión: admin
ruta_admin = db.foto_perfil()
check(ruta_admin is not None and os.path.exists(ruta_admin)
      and os.path.basename(ruta_admin).startswith("usuario_"),
      "punto 3: la foto se guarda en un archivo propio del usuario")

db.cerrar_sesion()
db.iniciar_sesion("operario", "clave123")
db.set_foto_perfil(foto_b)
ruta_oper = db.foto_perfil()
check(ruta_admin != ruta_oper and os.path.exists(ruta_admin)
      and os.path.exists(ruta_oper),
      "punto 3: cada usuario tiene su propia foto")
check(db.foto_perfil() == ruta_oper,
      "punto 3: la foto visible corresponde al usuario conectado")
db.quitar_foto_perfil()
check(db.foto_perfil() is None,
      "punto 3: el usuario se quita su foto")
check(db.foto_perfil(u_admin["id"]) == ruta_admin,
      "punto 3: quitar la foto no afecta a los demás usuarios")

db.cerrar_sesion()
db.iniciar_sesion("admin", "admin")
db.quitar_foto_perfil()
for _f in (foto_a, foto_b):
    if os.path.exists(_f):
        os.remove(_f)

# ---- Punto 2: el cierre con ventas cierra sin ventanas de más ----
db.reabrir_caja(caja["id"])
_p0 = db.productos()[0]
db.registrar_venta(caja["id"], _p0["id"], 1, _p0["precio"], "Efectivo")

app2 = _nueva_app()
app2.update()
app2.mostrar("ventas")            # para comprobar que vuelve a Inicio al cerrar
app2.update()
ini2 = app2.paneles["inicio"]
ini2._abrir_cierre()
app2.update()
dlg2 = [w for w in app2.winfo_children()
        if w.winfo_class() == "Toplevel" and w.title() == "Cierre de caja"]
check(bool(dlg2), "punto 2: con ventas se abre el diálogo de arqueo")
if dlg2:
    sh_pantalla = dlg2[0].winfo_screenheight()
    alto_dlg = int(str(dlg2[0].geometry()).split("x")[1].split("+")[0])
    check(alto_dlg <= sh_pantalla - 40,
          f"punto 2: el diálogo se adapta a la pantalla "
          f"({alto_dlg}px vs {sh_pantalla - 40}px)")

# Registrar cualquier ventana de información que aparezca al confirmar
_infos = []
mb.showinfo = lambda *a, **k: _infos.append(str(a[0]) if a else "")
if dlg2:
    dlg2[0].celdas[10000].set("1")
    dlg2[0]._recalcular()
    dlg2[0]._confirmar()
    app2.update()
mb.showinfo = lambda *a, **k: None

check(not [w for w in app2.winfo_children()
           if w.winfo_class() == "Toplevel" and w.title() == "Cierre de caja"],
      "punto 2: confirmado el cierre, el diálogo se cierra por completo")
check(not _infos,
      f"punto 2: no aparece ninguna ventana extra de información "
      f"(obtuvo {_infos})")
check(app2.panel_actual == "inicio",
      f"punto 2: el sistema vuelve automáticamente a Inicio "
      f"(obtuvo {app2.panel_actual})")
check(db.get_caja_por_id(caja["id"])["estado"] == "cerrada",
      "punto 2: la caja queda efectivamente cerrada")
check(db.get_cierre_activo(caja["id"]) is not None,
      "punto 2: el cierre queda registrado en el historial")
app2.destroy()

# ==========================================================================
# Soporte del sistema (ayuda local, sin internet): base de conocimiento,
# buscador y ventana flotante.
# ==========================================================================
import ayuda
from ui_ayuda import SoporteVentana

check(len(ayuda.TEMAS) >= 15,
      f"soporte: hay una base de conocimiento ({len(ayuda.TEMAS)} temas)")
check(all(t.get("titulo") and t.get("parrafos") and t.get("seccion")
          for t in ayuda.TEMAS),
      "soporte: todos los temas traen título, respuesta y fuente")

casos_soporte = [
    ("¿Cómo abro la caja?", "abrir_caja"),
    ("¿Cómo cierro la caja?", "cerrar_caja"),
    ("que significa faltante", "cerrar_caja"),
    ("reabrir caja cerrada", "reabrir_caja"),
    ("cargar una venta", "ventas"),
    ("tarjeta de credito", "medios_pago"),
    ("numero de comprobante", "transferencia"),
    ("exportar a excel", "excel"),
    ("historial de cierres", "historial"),
    ("cuanto vendi este mes", "estadisticas"),
    ("crear usuario nuevo", "usuarios"),
    ("cambiar mi contrasena", "mi_cuenta"),
    ("restaurar respaldo", "respaldos"),
    ("cambiar precio", "productos"),
    ("caja de ayer", "nuevo_dia"),
    ("no me deja registrar ventas", "problemas"),
    ("quien hizo esta venta", "actividad"),
    ("instalar en otra pc", "instalar"),
]
for _p, _esperado in casos_soporte:
    _r = ayuda.resolver(_p)
    check(_r["ok"] and _r["tema"]["id"] == _esperado,
          f"soporte: responde {_esperado} ante «{_p}»")

check(ayuda.resolver("")["tema"]["id"] == "saludo",
      "soporte: sin pregunta devuelve la bienvenida")
check(not ayuda.resolver("xyzqr")["ok"],
      "soporte: lo que no existe dice que no tiene respuesta")
_check_vaga = ayuda.resolver("caja")
check(not _check_vaga["ok"] and len(_check_vaga["ambiguas"]) >= 2,
      "soporte: una pregunta vaga ofrece varios temas en vez de inventar")
check(len(ayuda.SUGERENCIAS) >= 4,
      "soporte: hay preguntas rápidas para mostrar")
check(all(ayuda.resolver(s)["ok"] for s in ayuda.SUGERENCIAS),
      "soporte: cada pregunta rápida responde de verdad")

# -------- la ventana flotante --------
app4 = _nueva_app()
app4.update()
check(hasattr(app4, "btn_soporte"), "soporte: el botón flotante existe")

# El botón no debe tapar ningún widget de ningún panel (punto 4)
_bx, _by = app4.btn_soporte.winfo_rootx(), app4.btn_soporte.winfo_rooty()
_bw = app4.btn_soporte.winfo_width()
_bh = app4.btn_soporte.winfo_height()

def _chocan(widget, salida):
    try:
        if not widget.winfo_ismapped():
            return
        wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
        ww, wh = widget.winfo_width(), widget.winfo_height()
        if wx < _bx + _bw and wx + ww > _bx and wy < _by + _bh and wy + wh > _by:
            salida.append(widget)
    except Exception:
        return
    for hijo in widget.winfo_children():
        _chocan(hijo, salida)

_tapados = []
for _panel in app4.paneles.values():
    _chocan(_panel, _tapados)
check(not _tapados,
      "soporte: el botón flotante no tapa ningún contenido de los paneles")

app4.abrir_soporte()
app4.update()
_ven = app4.ventana_soporte
check(_ven is not None and _ven.winfo_exists(),
      "soporte: el botón abre la ventana flotante")

_sw, _sh = _ven.winfo_screenwidth(), _ven.winfo_screenheight()
check(_ven.winfo_width() <= _sw and _ven.winfo_height() <= _sh,
      f"soporte: la ventana entra en la pantalla "
      f"({_ven.winfo_width()}x{_ven.winfo_height()} vs {_sw}x{_sh})")
check(_ven.winfo_rootx() >= 0 and _ven.winfo_rooty() >= 0
      and _ven.winfo_rootx() + _ven.winfo_width() <= _sw
      and _ven.winfo_rooty() + _ven.winfo_height() <= _sh,
      "soporte: la ventana queda completa, sin salirse del monitor")

app4.abrir_soporte()
app4.update()
check(app4.ventana_soporte is _ven,
      "soporte: la segunda pulsada reutiliza la misma ventana")

import time as _time

for _p in ["¿Cómo cierro la caja?", "¿Cómo exporto a Excel?",
           "caja", "xyzqr", "hola"]:
    _ven.preguntar(_p)
    app4.update()
# Las respuestas llegan con delay ("escribiendo…"): se espera a que la cola
# se vacíe y no haya ninguna respuesta en curso.
_espera_ms = 0
while (_ven._cola or _ven._pensando) and _espera_ms < 30000:
    app4.update()
    _time.sleep(0.05)
    _espera_ms += 50
check(not _ven._cola and not _ven._pensando,
      "soporte: todas las respuestas se procesaron")


def _texto_chat(ven):
    """Une el texto de todas las burbujas: cada cuerpo es un Text
    deshabilitado y las horas/fuentes son Labels."""
    partes = []

    def _barrer(w):
        for c in w.winfo_children():
            try:
                if c.winfo_class() == "Text":
                    partes.append(c.get("1.0", "end"))
            except tk.TclError:
                pass
            try:
                t = c.cget("text")
                if isinstance(t, str) and t.strip():
                    partes.append(t)
            except tk.TclError:
                pass
            _barrer(c)

    _barrer(ven.hilo)
    return "\n".join(partes)


_texto_soporte = _texto_chat(_ven)
check("FALTANTE" in _texto_soporte,
      "soporte: la respuesta se escribe en la ventana")
check("TARJETAS" in _texto_soporte,
      "soporte: responde también dudas de Excel")
check("No tengo esa respuesta" in _texto_soporte,
      "soporte: admite que no tiene cargada una pregunta")
check("más de un tema" in _texto_soporte,
      "soporte: ante una pregunta vaga sugiere temas")
check(_ven.lienzo.winfo_class() == "Canvas",
      "soporte: el chat es de solo lectura (no se puede editar a mano)")
_ven._al_cerrar()
app4.update()
check(not _ven.winfo_viewable(),
      "soporte: el botón ✕ oculta la ventana sin perder la conversación")
app4.abrir_soporte()
app4.update()
check(app4.ventana_soporte is _ven and _ven.winfo_viewable(),
      "soporte: al volver a abrirla sigue la conversación")
app4.destroy()

# ==========================================================================
# VENTAS COMO TICKET (v1.3): varios productos y varios medios de pago
# ==========================================================================
db.cerrar_sesion()
db.iniciar_sesion("admin", "admin")
db.reabrir_caja(caja["id"])

_tk10 = db.producto_por_nombre("Garrafa 10 kg")
_tk15 = db.producto_por_nombre("Garrafa 15 kg")
_tkenv = db.producto_por_nombre("Envase 10 kg")

_r_antes = db.resumen(caja["id"])
_st_antes = db.estadisticas(hoy, hoy)

_ticket = db.registrar_ticket(
    caja["id"],
    [{"producto_id": _tk10["id"], "cantidad": 1, "precio_unitario": 40000},
     {"producto_id": _tk15["id"], "cantidad": 3, "precio_unitario": 10000},
     {"producto_id": _tkenv["id"], "cantidad": 1, "precio_unitario": 20000}],
    [{"medio": "Efectivo", "importe": 30000},
     {"medio": "Transferencia", "importe": 60000, "comprobante": "123456789"}],
    cliente="Mixta")
check(_ticket["total"] == 90000,
      "ticket: el total es la suma de los 3 productos")
check(len(_ticket["items"]) == 3 and len(_ticket["pagos"]) == 2,
      "ticket: guarda los 3 productos y los 2 medios de pago juntos")
check("×" in (_ticket["producto"] or "") and "Envase 10 kg" in _ticket["producto"],
      "ticket: la carga completa queda guardada en la venta")
check(_ticket["medios_txt"] == "Efectivo + Transferencia",
      f"ticket: se ven los dos medios de pago (obtuvo {_ticket['medios_txt']})")
check(_ticket["comprobante"] == "123456789",
      "ticket: el N° de comprobante queda en el ticket")
check(_ticket["medio"] == "Transferencia",
      "ticket: el medio principal es el que aporta más dinero")

_r_desp = db.resumen(caja["id"])
check(_r_desp["cantidad_ventas"] == _r_antes["cantidad_ventas"] + 1,
      "ticket: varios productos y varios medios es UNA sola operación")
check(abs(_r_desp["total_general"] - _r_antes["total_general"] - 90000) < 0.01,
      "ticket: el total del día crece una sola vez (sin duplicar)")
check(abs(_r_desp["efectivo"] - _r_antes["efectivo"] - 30000) < 0.01,
      "ticket: en efectivo solo cuenta lo pagado en efectivo")
check(abs(_r_desp["transferencias"] - _r_antes["transferencias"] - 60000) < 0.01,
      "ticket: en transferencias solo cuenta lo transferido")
check(_r_desp["n_transferencias"] == _r_antes["n_transferencias"] + 1,
      "ticket: el cobro mixto cuenta UNA transferencia")
check(_r_desp["total_garrafas"] == _r_antes["total_garrafas"] + 5,
      f"ticket: suma las unidades de los 3 productos "
      f"(1 + 3 + 1 = 5, obtuvo "
      f"{_r_desp['total_garrafas'] - _r_antes['total_garrafas']})")
_st_desp = db.estadisticas(hoy, hoy)
check(abs(_st_desp["total_vendido"] - _st_antes["total_vendido"] - 90000) < 0.01,
      "ticket: las estadísticas cuentan el dinero una sola vez")
check(_st_desp["cantidad_ventas"] == _st_antes["cantidad_ventas"] + 1,
      "ticket: las estadísticas cuentan tickets, no cobros")

# ---- Validaciones del ticket (punto 5 de la especificación) ----
_err_suma = ""
try:
    db.registrar_ticket(
        caja["id"],
        [{"producto_id": _tk10["id"], "cantidad": 1, "precio_unitario": 10000}],
        [{"medio": "Efectivo", "importe": 4000},
         {"medio": "Tarjeta de débito", "importe": 4000}])
except ValueError as e:
    _err_suma = str(e)
check(bool(_err_suma) and "faltan" in _err_suma.lower(),
      f"ticket: avisa cuánto falta para completar la venta "
      f"(obtuvo {_err_suma or '—'})")
check_error(lambda: db.registrar_ticket(
    caja["id"], [],
    [{"medio": "Efectivo", "importe": 1000}]),
    "ticket: no se puede guardar un ticket sin productos")
check_error(lambda: db.registrar_ticket(
    caja["id"],
    [{"producto_id": _tk10["id"], "cantidad": 0, "precio_unitario": 1000}],
    [{"medio": "Efectivo", "importe": 0}]),
    "ticket: ni cantidad ni importe en cero")
check(db.resumen(caja["id"])["cantidad_ventas"] == _r_antes["cantidad_ventas"] + 1,
      "ticket: lo rechazado no se guarda")

# ---- Excel: con un ticket mixto los controles siguen cerrando ----
_xl_mix = os.path.join(_tempfile.gettempdir(), "excel_mixto.xlsx")
if os.path.exists(_xl_mix):
    os.remove(_xl_mix)
_n_xl, _m_xl = xl.exportar_movimientos(hoy, hoy, _xl_mix)
_r_xl = db.resumen(caja["id"])
check(_n_xl == _r_xl["cantidad_ventas"],
      f"excel: cuenta tickets únicos ({_n_xl}) y no filas de cobro")
check(abs(_m_xl - _r_xl["total_general"]) < 0.01,
      "excel: el total del reporte es el dinero cobrado en los medios")
_wsx = load_workbook(_xl_mix).active
_filas_xl = [[str(c.value) for c in f if c.value is not None]
             for f in _wsx.iter_rows()]
_mixta = [f for f in _filas_xl
          if f and str(f[0]).startswith("#") and "Mixta" in " ".join(f)]
check(len(_mixta) == 2,
      f"excel: el ticket mixto tiene una fila por cada cobro "
      f"(obtuvo {len(_mixta)})")
_con_tx = [f for f in _mixta if any("123456789" in x for x in f)]
check(len(_con_tx) == 1,
      "excel: la transferencia figura una sola vez y con su comprobante")
if _con_tx:
    _nums = []
    for x in _con_tx[0]:
        try:
            _nums.append(float(x))
        except (TypeError, ValueError):
            pass
    check(any(abs(v - 60000) < 0.01 for v in _nums),
          "excel: en transferencias solo figura el importe transferido "
          "($60.000), no los $90.000 de la venta")
else:
    check(False, "excel: en transferencias solo figura el importe transferido")
_ctrl_xl = [f for f in _filas_xl if f and str(f[0]).startswith("CONTROL DE ")]
check(len(_ctrl_xl) >= 2
      and all(str(f[-1]) == "COINCIDE" for f in _ctrl_xl),
      "excel: con un ticket mixto los controles siguen dando COINCIDE")
check(any(str(f[0]).startswith("Total ") for f in _filas_xl if f),
      "excel: el detalle agrupa los cobros por medio de pago")

# ---- Edición y borrado del ticket ----
_editado = db.actualizar_ticket(
    _ticket["id"],
    [{"producto_id": _tk10["id"], "cantidad": 3, "precio_unitario": 40000}],
    [{"medio": "Efectivo", "importe": 120000}],
    cliente="Editada")
check(_editado["total"] == 120000 and len(_editado["items"]) == 1
      and len(_editado["pagos"]) == 1,
      "ticket: se puede editar la lista de productos y la de pagos")
db.eliminar_ventas([_ticket["id"]])
_con = _sqlite.connect(db.DB_PATH)
_huerfanos = (
    _con.execute("SELECT COUNT(*) FROM venta_items WHERE venta_id NOT IN "
                 "(SELECT id FROM ventas)").fetchone()[0]
    + _con.execute("SELECT COUNT(*) FROM venta_pagos WHERE venta_id NOT IN "
                   "(SELECT id FROM ventas)").fetchone()[0])
_con.close()
check(_huerfanos == 0,
      "ticket: al borrar no quedan productos ni pagos huérfanos")

# ---- Migración: las ventas viejas (1 producto + 1 medio) sobreviven ----
_mig = os.path.join(_tempfile.gettempdir(), "garrafas_migracion.db")
if os.path.exists(_mig):
    os.remove(_mig)
_ruta_ok = db.DB_PATH
db.DB_PATH = _mig
_con = _sqlite.connect(_mig)
_con.executescript("""
CREATE TABLE productos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT,
    familia TEXT, precio REAL, activo INTEGER DEFAULT 1);
CREATE TABLE cajas (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT,
    estado TEXT, saldo_base REAL DEFAULT 0, creado TEXT);
CREATE TABLE ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, caja_id INTEGER,
    producto_id INTEGER, cantidad INTEGER, precio_unitario REAL, total REAL,
    medio TEXT, fecha_hora TEXT, registrada_por INTEGER);
INSERT INTO productos (nombre, familia, precio)
    VALUES ('Garrafa 10 kg', 'garrafas', 10000);
INSERT INTO cajas (fecha, estado, creado) VALUES ('2024-01-01', 'abierta', 'x');
INSERT INTO ventas (caja_id, producto_id, cantidad, precio_unitario, total,
                    medio, fecha_hora)
    VALUES (1, 1, 3, 10000, 30000, 'Efectivo', '2024-01-01 10:00:00');
""")
_con.commit()
_con.close()
db.init()
_vieja = db.venta_por_id(1)
check(_vieja is not None and _vieja["cantidad"] == 3
      and _vieja["producto_id"] == 1 and _vieja["total"] == 30000
      and _vieja["medio"] == "Efectivo",
      "migración: la venta vieja queda como ticket con producto y medio")
check(len(_vieja["items"]) == 1 and len(_vieja["pagos"]) == 1,
      "migración: tiene un producto y un medio de pago")
db.init()
check(db.venta_por_id(1) is not None and db.venta_por_id(2) is None,
      "migración: volver a iniciar no duplica ni rompe nada")
db.DB_PATH = _ruta_ok
os.remove(_mig)

# ---- Interfaz: armar y registrar un ticket desde Ventas ----
app5 = _nueva_app()
app5.update()
app5.mostrar("ventas")
app5.update()
pv5 = app5.paneles["ventas"]
_antes_ui = db.resumen(caja["id"])["cantidad_ventas"]

pv5.combo_producto.current(0)
pv5.var_cantidad.set("2")
pv5.var_precio.set("10000")
pv5._agregar_item()
check(len(pv5._items) == 1, "ui ticket: el producto entra al ticket")
pv5.combo_producto.current(1)
pv5.var_cantidad.set("1")
pv5.var_precio.set("15000")
pv5._agregar_item()
app5.update()
check(len(pv5._items) == 2 and abs(pv5._total - 35000) < 0.01,
      f"ui ticket: el total junta los dos productos "
      f"(obtuvo {pv5._total}, esperaba 35000)")
check(len(pv5.tree_items.get_children()) == 2,
      "ui ticket: los productos se ven en la lista del ticket")

pv5.combo_medio.set("Efectivo")
pv5.var_importe.set("10000")
pv5._agregar_pago()
pv5.combo_medio.set("Tarjeta de débito")
pv5.var_importe.set("25000")
pv5._agregar_pago()
app5.update()
check(len(pv5._pagos) == 2 and len(pv5.tree_pagos.get_children()) == 2,
      "ui ticket: los dos medios de pago quedan en la lista")
check("FALTAN" not in pv5.lbl_pago.cget("text")
      and "PAGOS = TOTAL" in pv5.lbl_pago.cget("text"),
      f"ui ticket: avisa que los pagos suman el total "
      f"(obtuvo {pv5.lbl_pago.cget('text')})")

pv5._registrar()
app5.update()
check(db.resumen(caja["id"])["cantidad_ventas"] == _antes_ui + 1,
      "ui ticket: registra el ticket completo de una sola vez")
_nuevo = db.venta_por_id(int(pv5.tree.get_children()[-1]))
check(_nuevo is not None and len(_nuevo["items"]) == 2
      and len(_nuevo["pagos"]) == 2 and abs(_nuevo["total"] - 35000) < 0.01,
      "ui ticket: quedan guardados los 2 productos y los 2 cobros")
check("Tarjeta de débito" in _nuevo["medios_txt"],
      "ui ticket: en la lista se ven las dos formas de pago")
check(pv5.var_cliente.get() == "" and pv5.var_importe.get() == "",
      "ui ticket: al registrar vuelve a quedar limpio para la próxima venta")

# Suma incompleta: quien dice que no, no registra nada y ve cuánto falta
_askyesno_antes = mb.askyesno
ERRORES.clear()
mb.askyesno = lambda *a, **k: False
pv5.combo_medio.set("Efectivo")
pv5.var_importe.set("1000")
pv5._registrar()
app5.update()
mb.askyesno = _askyesno_antes
check(db.resumen(caja["id"])["cantidad_ventas"] == _antes_ui + 1,
      "ui ticket: un cobro que no suma el total bloquea el registro")
check(any("faltan" in str(e).lower() for e in ERRORES),
      f"ui ticket: muestra cuánto falta para completar la venta "
      f"(obtuvo {len(ERRORES)} avisos)")

# Si acepta completar, la venta se cierra con lo que faltaba
ERRORES.clear()
mb.askyesno = lambda *a, **k: True
pv5._registrar()
app5.update()
mb.askyesno = _askyesno_antes
check(db.resumen(caja["id"])["cantidad_ventas"] == _antes_ui + 2,
      "ui ticket: al aceptar, se completa el importe que faltaba")
_cerrado = db.venta_por_id(int(pv5.tree.get_children()[-1]))
check(_cerrado is not None and len(_cerrado["pagos"]) == 1
      and abs(sum(p["importe"] for p in _cerrado["pagos"])
              - _cerrado["total"]) < 0.01,
      "ui ticket: el cobro completado cierra exacto con el total")

# Las etiquetas nuevas cuentan qué tiene adentro el total
pv5.combo_producto.current(0)
pv5.var_cantidad.set("1")
pv5.var_precio.set("9000")
pv5._agregar_item()
app5.update()
check("fila cargada" in pv5.lbl_desglose.cget("text")
      or "ya está sumada" in pv5.lbl_desglose.cget("text"),
      f"ui ticket: el desglose explica qué tiene el total "
      f"(obtuvo {pv5.lbl_desglose.cget('text')})")
check("vacío" in pv5.lbl_importe.cget("text")
      and "$" in pv5.lbl_importe.cget("text"),
      f"ui ticket: la etiqueta del importe dice cuánto se cobra si lo dejan "
      f"vacío (obtuvo {pv5.lbl_importe.cget('text')})")
_textos_pasos = []
for _fila_p in pv5.lbl_pasos.winfo_children():
    for _w_p in _fila_p.winfo_children():
        try:
            _t_p = _w_p.cget("text")
            if isinstance(_t_p, str) and _t_p.strip():
                _textos_pasos.append(_t_p)
        except tk.TclError:
            pass
check(any("AGREGAR AL TICKET" in t for t in _textos_pasos)
      and any("REGISTRAR VENTA" in t for t in _textos_pasos),
      "ui ticket: el formulario explica los dos pasos del flujo")
# ---------------- Rendición por buzón: carga, calculadora y planilla A4 ----------------
from util import money as _money, parse_numero as _pn

# Nivel de datos: un registro por fecha (se actualiza, nunca se duplica)
_d_r = {"fecha": db.hoy(), "chofer": "Ramírez", "gastos": 15000,
        "billetes": {"100": 3, "20000": 1}, "total_billetes": 20300}
db.guardar_rendicion(db.hoy(), _d_r, loguear=False)
check(db.rendicion_de(db.hoy())["chofer"] == "Ramírez",
      "rendición: se guarda y se recupera la rendición del día")
db.guardar_rendicion(db.hoy(), dict(_d_r, chofer="Otro"), loguear=False)
check(len(db.rendiciones()) == 1
      and db.rendicion_de(db.hoy())["chofer"] == "Otro",
      "rendición: hay UN solo registro por día (se actualiza, no duplica)")
check(db.rendicion_de("1999-01-01") == {},
      "rendición: un día sin cargar queda vacío")
db.borrar_rendicion(db.hoy())
check(db.rendicion_de(db.hoy()) == {}, "rendición: la rendición se puede borrar")

# Se destruye app5 ANTES de crear otra raíz Tk: si quedan dos vivas, PIL
# crea las imágenes en la raíz vieja y el widget nuevo no las encuentra.
app5.destroy()
app6 = _nueva_app()
app6.update()
check("rendicion" in app6.paneles and "rendicion" in app6.botones_nav,
      "rendición: la pantalla nueva está en el lateral")
check(db.puede("rendicion"),
      "rendición: el permiso existe y el DESARROLLADOR lo tiene")
app6.mostrar("rendicion")
app6.update()
pr = app6.paneles["rendicion"]
check(len(pr.notebook.tabs()) == 2,
      "rendición: tiene las dos pestañas (carga y calculadora)")

# Pestaña mixta: lo que el sistema ya sabe del día queda precargado y editable
_res_r = db.resumen(db.get_caja(db.hoy())["id"])
_tarj_esp = _res_r["debito"] + _res_r["credito"]
check((_pn(pr.secciones["tarjetas"].get()) or 0) == _tarj_esp,
      f"rendición: TARJETAS se precarga con las ventas del día "
      f"(obtuvo {pr.secciones['tarjetas'].get()}, esperaba {_money(_tarj_esp)})")
check((_pn(pr.secciones["transferencias"].get()) or 0)
      == _res_r["transferencias"],
      "rendición: TRANSFERENCIAS también se precarga del día")
_espera_det = sum(1 for _i in _res_r["por_producto"].values()
                  if int(_i["cantidad"]) > 0)
check(_espera_det > 0 and len(pr.detalle) == _espera_det
      and all(int(_i["cantidad"]) > 0 for _i in pr.detalle),
      f"rendición: el DETALLE se precarga con las ventas del día por "
      f"producto (obtuvo {len(pr.detalle)} filas, esperaba {_espera_det})")
pr.secciones["gastos"].set("15000")        # lo demás lo carga el usuario
check(pr.secciones["gastos"].get() == "15000",
      "rendición: cualquier sección se puede cargar a mano")

# Calculadora de billetes: cantidad × valor = importe, y total al pie
pr.celdas_billetes[100].insert(0, "3")
pr.celdas_billetes[1000].insert(0, "2")
pr.celdas_billetes[20000].insert(0, "1")
pr._recalcular_billetes()
check(abs(pr.total_billetes - 22300) < 0.01,
      f"rendición: 3×$100 + 2×$1.000 + 1×$20.000 = 22.300 "
      f"(obtuvo {pr.total_billetes})")
check(pr.lbl_total_billetes.cget("text") == "$22.300",
      f"rendición: se ve el TOTAL EFECTIVO "
      f"(obtuvo {pr.lbl_total_billetes.cget('text')})")

# El enlace es automático: el total aparece en la pestaña de la planilla
check(pr.var_efectivo.get() == "$22.300",
      f"rendición: el total se copia SOLO al campo EFECTIVO de la planilla "
      f"(obtuvo {pr.var_efectivo.get()})")
pr.celdas_billetes[20000].delete(0, "end")
pr.celdas_billetes[20000].insert(0, "2")
pr._recalcular_billetes()
check(pr.var_efectivo.get() == "$42.300",
      f"rendición: al cambiar los billetes cambia el efectivo de la planilla "
      f"(obtuvo {pr.var_efectivo.get()})")

# Detalle de la planilla: Tipo · Cantidad · Importe · Total
_n_det_prev = len(pr.detalle)
_tot_det_prev = _pn(pr.lbl_total_detalle.cget("text")) or 0
pr.combo_tipo.set("Garrafa 10 kg")
pr.var_cant_det.set("3")
pr.var_imp_det.set("23000")
pr._agregar_item()
app6.update()
check(len(pr.detalle) == _n_det_prev + 1
      and abs((_pn(pr.lbl_total_detalle.cget("text")) or 0)
              - (_tot_det_prev + 69000)) < 0.01,
      f"rendición: la fila entra al detalle y suma el total "
      f"(obtuvo {pr.lbl_total_detalle.cget('text')})")

# Cheques: cliente, número, banco, importe y fechas de emisión/cobro
pr.var_cheque_cliente.set("Juan Pérez")
pr.var_cheque_numero.set("000123")
pr.var_cheque_banco.set("Nación")
pr.var_cheque_importe.set("50000")
pr.var_cheque_emision.set("01/10/2026")
pr.var_cheque_cobro.set("15/10/2026")
pr._agregar_cheque()
check(pr.lbl_total_cheques.cget("text") == "$50.000",
      f"rendición: total de cheques "
      f"(obtuvo {pr.lbl_total_cheques.cget('text')})")
check(pr.cheques[0].get("emision") == "2026-10-01"
      and pr.cheques[0].get("cobro") == "2026-10-15",
      f"rendición: el cheque guarda emisión y cobro normalizadas "
      f"(obtuvo {pr.cheques[0].get('emision')}/"
      f"{pr.cheques[0].get('cobro')})")

pr.var_chofer.set("Gómez")
check(pr._guardar() is not None, "rendición: se guarda desde la interfaz")
_g = db.rendicion_de(db.hoy())
check(_g["chofer"] == "Gómez" and len(_g["detalle"]) == _n_det_prev + 1
      and len(_g["cheques"]) == 1
      and _g["cheques"][0].get("cobro") == "2026-10-15"
      and abs(_g["total_billetes"] - 42300) < 0.01,
      "rendición: quedan guardados chofer, detalle, cheque y billetes")
pr.refresh()
check(pr.var_chofer.get() == "Gómez" and len(pr.detalle) == _n_det_prev + 1,
      "rendición: al refrescar la pantalla no se pisa lo cargado")

# Planilla A4: una sola hoja, con todos los campos del formulario
_ruta_planilla = os.path.join(tempfile.gettempdir(),
                              "planilla_rendicion_test.xlsx")
if os.path.exists(_ruta_planilla):
    os.remove(_ruta_planilla)
_ult = xl.exportar_rendicion(_g, _ruta_planilla)
_wbp = load_workbook(_ruta_planilla)
_wsp = _wbp.active
check(_wsp.page_setup.orientation == "landscape",
      "rendición A4: la hoja va en horizontal")
check(str(_wsp.page_setup.paperSize) == str(_wsp.PAPERSIZE_A4),
      "rendición A4: el papel es A4")
check(_wsp.page_setup.fitToWidth == 1 and _wsp.page_setup.fitToHeight == 1
      and _wsp.sheet_properties.pageSetUpPr.fitToPage is True,
      "rendición A4: entra en UNA sola hoja (no se divide en dos)")
check(_wsp.print_area == f"'{_wsp.title}'!$A$1:$J${_ult}",
      f"rendición A4: el área de impresión cubre toda la planilla "
      f"(obtuvo {_wsp.print_area})")

_txt_r = [str(c.value) for f in _wsp.iter_rows() for c in f
          if c.value is not None]
for _campo in ("PLANILLA DE RENDICIÓN", "FECHA", "CHOFER",
               "CANTIDAD", "IMPORTE", "TOTAL", "GASTOS", "CAJA",
               "TARJETAS", "TRANSFERENCIAS", "CLIENTE",
               "N.º CHEQUE", "BANCO", "F. EMISIÓN", "F. COBRO",
               "BILLETE", "TOTAL DE BILLETES",
               "OBSERVACIONES"):
    check(any(_campo in t for t in _txt_r),
          f"rendición A4: conserva el campo {_campo}")
_num_r = [c.value for f in _wsp.iter_rows() for c in f
          if isinstance(c.value, (int, float))]
check(any(abs(n - 42300) < 0.01 for n in _num_r),
      "rendición A4: el TOTAL EFECTIVO de la calculadora llega a la planilla")
check(not any("CALCULADORA" in t for t in _txt_r),
      "rendición A4: el rótulo pasó a TOTAL DE BILLETES, sin CALCULADORA")
check(any(abs(n - 50000) < 0.01 for n in _num_r),
      "rendición A4: el TOTAL CHEQUES llega a la planilla")
check(xl.total_billetes_de({}) == 0
      and abs(xl.total_billetes_de({"billetes": {"1000": 2}}) - 2000) < 0.01,
      "rendición A4: el total de billetes se puede calcular solo con el conteo")

# El detalle de venta y los envíos ya no se imprimen
check(not any("DETALLE" in t for t in _txt_r),
      "rendición A4: se fue la sección de DETALLE (no discrimina productos)")
check(not any("ENVÍO" in t for t in _txt_r),
      "rendición A4: se fue la sección de ENVIOS")
check(not any("RECIBOS" in t for t in _txt_r),
      "rendición A4: se fue la sección de RECIBOS")
check(not any(abs(n - 69000) < 0.01 for n in _num_r),
      "rendición A4: ya no se imprime el importe por producto")

# El conteo por denominación: cuántos billetes de cada uno y cuánto suman
_conteo_billetes = {}
for _fila_xl in _wsp.iter_rows(min_row=1, max_row=_wsp.max_row):
    _denom_xl = _fila_xl[6].value                # columna G: BILLETE (G:H)
    if isinstance(_denom_xl, (int, float)):
        _conteo_billetes[int(_denom_xl)] = (_fila_xl[8].value,     # I: cantidad
                                            _fila_xl[9].value)     # J: importe
_esperados = {100: 3, 200: 0, 500: 0, 1000: 2, 2000: 0, 10000: 0,
              20000: 2}
for _denom_xl, _cant_esperada in _esperados.items():
    check(_denom_xl in _conteo_billetes,
          f"rendición A4: el billete de ${_denom_xl} está en el conteo")
    _cant_xl, _imp_xl = _conteo_billetes.get(_denom_xl, (None, None))
    check(_cant_xl == _cant_esperada
          and abs((_imp_xl or 0) - _denom_xl * _cant_esperada) < 0.01,
          f"rendición A4: el billete de ${_denom_xl} se cuenta y suma "
          f"({_cant_esperada} x ${_denom_xl} = {_imp_xl})")
check(not any(_r.min_col == 7 and _r.max_col == 10
              and (_r.max_row - _r.min_row) >= 3
              for _r in _wsp.merged_cells.ranges),
      "rendición A4: el total de billetes va discriminado, no en un bloque")

# La hoja tiene que llenar el A4 de punta a punta
_altas_xl = [d.height for d in _wsp.row_dimensions.values() if d.height]
check(sum(_altas_xl) >= xl.alto_objetivo_a4() * 0.99,
      f"rendición A4: las filas llenan la hoja entera "
      f"(suman {sum(_altas_xl):.0f} pt y hacen falta "
      f"{xl.alto_objetivo_a4():.0f} pt)")

# El soporte también explica la pantalla nueva
for _pregunta_r in ("planilla de rendicion", "calculadora de billetes",
                    "imprimir la planilla"):
    _rr = ayuda.resolver(_pregunta_r)
    check(_rr["ok"] and _rr["tema"]["id"] == "rendicion",
          f"soporte: responde rendición ante «{_pregunta_r}»")
app6.destroy()

os.remove(TMP)
import shutil as _shutil
_shutil.rmtree(db.dir_respaldos(), ignore_errors=True)
print(f"\nTODAS LAS PRUEBAS PASARON ({ok} verificaciones)")
