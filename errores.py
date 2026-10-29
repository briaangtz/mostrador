# -*- coding: utf-8 -*-
"""
Errores inesperados: cartel genérico para el usuario, detalle al archivo.

Hallazgo AppSec #10: varios carteles mostraban ``str(exc)`` a pantalla.
El texto de una excepción puede contener rutas del disco, mensajes de
SQLite u otros detalles internos que el usuario no necesita ver.

Con este módulo:

  * el usuario ve un cartel GENÉRICO (qué operación falló y qué hacer),
  * el detalle completo, con la traza, queda en ``errores.log``
    junto al programa, para quien tenga que diagnosticar el problema.

Uso en un ``except``::

    try:
        db.respaldar("manual")
    except Exception as exc:
        errores.mostrar("Respaldo", exc, parent=self,
                        contexto="generar respaldo",
                        mensaje="No se pudo generar el respaldo.")
        return
"""

import logging
import logging.handlers
import os
import sys

# Carpeta de datos: junto al .exe si está compilado, o junto al código
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RUTA_LOG = os.path.join(BASE_DIR, "errores.log")

MENSAJE_GENERICO = ("No se pudo completar la operación.\n\n"
                    "El detalle quedó guardado en errores.log (junto al "
                    "programa). Si vuelve a pasar, mostrale ese archivo "
                    "al encargado del sistema.")

_logger = logging.getLogger("mostrador.errores")


def _asegurar_log():
    """Arma (o reapunta) el archivo de log. Crea errores.log al primer uso."""
    destino = os.path.abspath(RUTA_LOG)
    for h in list(_logger.handlers):
        if getattr(h, "baseFilename", None) == destino:
            return
        _logger.removeHandler(h)
        h.close()
    manejador = logging.handlers.RotatingFileHandler(
        destino, maxBytes=512_000, backupCount=1, encoding="utf-8",
        delay=True)
    manejador.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(manejador)
    _logger.setLevel(logging.INFO)


def registrar(exc, contexto=""):
    """Vuelca el error completo (con traza) en errores.log."""
    _asegurar_log()
    _logger.error("Error%s: %s", (" en " + contexto) if contexto else "",
                  exc, exc_info=exc)


def mostrar(titulo, exc, parent=None, contexto="", mensaje=None):
    """Registra el error y muestra un cartel genérico (sin detalles internos).

    titulo   — del cartel (ya dice qué operación falló).
    exc      — la excepción capturada (para el log, nunca para el usuario).
    contexto — texto corto para el log ("generar respaldo", "cerrar caja"…).
    mensaje  — aclaración amable opcional bajo el título.
    """
    registrar(exc, contexto)
    try:
        from tkinter import messagebox
        messagebox.showerror(titulo, mensaje or MENSAJE_GENERICO,
                             parent=parent)
    except Exception:                # pragma: no cover
        pass                         # sin interfaz (pruebas/headless)
