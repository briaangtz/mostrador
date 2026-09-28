# -*- coding: utf-8 -*-
"""
Rangos y permisos del sistema.

Diseñado para ser extensible: para agregar un rango nuevo alcanza con
agregarlo a RANGOS y asignarle permisos en PERMISOS, sin tocar el resto
del sistema.
"""

# Rangos disponibles (el primero es el de mayor nivel)
RANGOS = ["DESARROLLADOR", "USUARIO"]

# Permiso -> lista de rangos que lo poseen (valores por defecto).
# Un usuario con permisos asignados a mano usa ESA lista en vez de estas.
PERMISOS = {
    # --- Cajas ---
    "abrir_caja":         ["DESARROLLADOR", "USUARIO"],
    "cerrar_caja":        ["DESARROLLADOR", "USUARIO"],
    "reabrir_caja":       ["DESARROLLADOR"],
    # --- Ventas y cobros (movimientos de dinero) ---
    "ventas":             ["DESARROLLADOR", "USUARIO"],
    "pago_efectivo":      ["DESARROLLADOR", "USUARIO"],
    "pago_transferencia": ["DESARROLLADOR", "USUARIO"],
    "pago_debito":        ["DESARROLLADOR", "USUARIO"],
    "pago_credito":       ["DESARROLLADOR", "USUARIO"],
    # --- Secciones del sistema ---
    "historial":          ["DESARROLLADOR", "USUARIO"],
    "estadisticas":       ["DESARROLLADOR"],
    "configuracion":      ["DESARROLLADOR"],
    "panel_admin":        ["DESARROLLADOR"],
    "admin_usuarios":     ["DESARROLLADOR"],
    "ver_actividad":      ["DESARROLLADOR"],
    # --- Reportes y perfil ---
    "exportar_excel":     ["DESARROLLADOR"],
    "cambiar_mia_clave":  ["DESARROLLADOR", "USUARIO"],
}

# Descripción legible de cada permiso (para el diálogo "Ver permisos")
DESCRIPCIONES = {
    "abrir_caja": "Abrir la caja del día registrando el monto inicial (fondo)",
    "cerrar_caja": "Realizar el arqueo y cerrar la caja",
    "reabrir_caja": "Reabrir una caja ya cerrada (requiere contraseña)",
    "ventas": "Registrar, editar y eliminar ventas en la caja del día",
    "pago_efectivo": "Registrar ventas cobradas en efectivo",
    "pago_transferencia": "Registrar ventas pagadas con transferencia "
                          "(con comprobante obligatorio)",
    "pago_debito": "Registrar pagos con tarjeta de débito",
    "pago_credito": "Registrar pagos con tarjeta de crédito",
    "historial": "Consultar el historial y el detalle de los cierres de caja",
    "estadisticas": "Consultar la sección de Estadísticas",
    "configuracion": "Modificar precios de productos, fondo inicial y "
                     "parámetros generales",
    "panel_admin": "Acceder al Panel de Administración",
    "admin_usuarios": "Crear, modificar, activar/desactivar y eliminar usuarios; "
                      "asignar rangos, contraseñas y permisos",
    "ver_actividad": "Consultar el registro de actividad del sistema",
    "exportar_excel": "Exportar los movimientos del período a Excel",
    "cambiar_mia_clave": "Cambiar la propia contraseña",
}

# Etiqueta corta para las casillas de permisos del panel de administración
ETIQUETAS = {
    "abrir_caja": "Abrir caja",
    "cerrar_caja": "Cerrar caja",
    "reabrir_caja": "Reabrir caja cerrada",
    "ventas": "Registrar ventas",
    "pago_efectivo": "Cobrar en Efectivo",
    "pago_transferencia": "Registrar Transferencias",
    "pago_debito": "Cobrar con Débito",
    "pago_credito": "Cobrar con Crédito",
    "historial": "Ver Historial de cierres",
    "estadisticas": "Ver Estadísticas",
    "configuracion": "Ver Configuración",
    "panel_admin": "Panel de Administración",
    "admin_usuarios": "Administrar usuarios",
    "ver_actividad": "Ver registro de actividad",
    "exportar_excel": "Exportar a Excel",
    "cambiar_mia_clave": "Cambiar mi contraseña",
}

# Agrupación de los permisos para la casilla por casilla del administrador
GRUPOS = [
    ("CAJAS", ["abrir_caja", "cerrar_caja", "reabrir_caja"]),
    ("VENTAS Y COBROS", ["ventas", "pago_efectivo", "pago_transferencia",
                         "pago_debito", "pago_credito"]),
    ("SECCIONES", ["historial", "estadisticas", "configuracion",
                   "panel_admin", "admin_usuarios", "ver_actividad"]),
    ("REPORTES Y PERFIL", ["exportar_excel", "cambiar_mia_clave"]),
]


def puede(permiso, rango):
    """True si el rango tiene el permiso indicado."""
    if not rango:
        return False
    return rango in PERMISOS.get(permiso, [])


def permisos_de(rango):
    """Lista de permisos que posee un rango."""
    return [p for p, rangos in PERMISOS.items() if rango in rangos]


def es_desarrollador(rango):
    return rango == "DESARROLLADOR"
