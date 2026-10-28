# -*- coding: utf-8 -*-
"""Prueba que SOLO en la planilla A4 de rendición, la fila EFECTIVO
(BILLETES) muestra el conteo ya descontando los gastos del día."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Consola Windows (cp1252): sin esto, imprimir "−" corta la ejecución.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from openpyxl import load_workbook
import excel as xl

ok = 0


def check(cond, msg):
    global ok
    if not cond:
        raise AssertionError(msg)
    ok += 1
    print("  OK:", msg)


def exportar(datos):
    ruta = os.path.join(tempfile.gettempdir(), "planilla_gastos_test.xlsx")
    if os.path.exists(ruta):
        os.remove(ruta)
    xl.exportar_rendicion(datos, ruta)
    return load_workbook(ruta).active


def valor_efectivo(ws):
    """Valor de la fila EFECTIVO (BILLETES) (rótulo en A, importe en F)."""
    for f in ws.iter_rows():
        for c in f:
            if c.value == "EFECTIVO (BILLETES)":
                return ws.cell(row=c.row, column=6).value
    return None


def valor_total_tabla(ws):
    """TOTAL de la tabla de denominaciones (rótulo en G, importe en I)."""
    for f in ws.iter_rows():
        for c in f:
            if c.column == 7 and c.value == "TOTAL":
                return ws.cell(row=c.row, column=9).value
    return None


# Conteos: 3×$100 + 2×$1.000 + 1×$20.000 = $42.300
conteo = {"100": 3, "1000": 2, "20000": 1}

# --- Sin gastos: la fila muestra el conteo tal cual ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X", "gastos": 0,
               "billetes": conteo, "total_billetes": 42300})
check(abs(valor_efectivo(ws) - 42300) < 0.01,
      f"sin gastos: EFECTIVO (BILLETES) = 42.300 (obtuvo {valor_efectivo(ws)})")

# --- Con gastos: la fila EFECTIVO (BILLETES) queda descontada ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X", "gastos": 50000,
               "billetes": conteo, "total_billetes": 42300})
check(abs(valor_efectivo(ws) - (42300 - 50000)) < 0.01,
      f"con gastos 50.000: EFECTIVO (BILLETES) = -7.700 "
      f"(obtuvo {valor_efectivo(ws)})")

# --- El TOTAL de la tabla de denominaciones NO se toca ---
check(abs(valor_total_tabla(ws) - 42300) < 0.01,
      f"el TOTAL de la tabla de billetes sigue = 42.300 "
      f"(obtuvo {valor_total_tabla(ws)})")

# --- Gastos guardados como vacío/cero (lo que guarda la UI) ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X", "gastos": 0.0,
               "billetes": conteo, "total_billetes": 42300})
check(abs(valor_efectivo(ws) - 42300) < 0.01,
      "gastos 0.0 (vacío en la UI) no altera la fila")

# --- Gastos en formato texto tipo "50.000" (por si llega de otra vía) ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X", "gastos": "50000",
               "billetes": conteo, "total_billetes": 42300})
check(abs(valor_efectivo(ws) - (-7700)) < 0.01,
      "gastos en formato texto se leen igual")

# --- Rendición sin campo gastos (registros viejos) ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X",
               "billetes": conteo, "total_billetes": 42300})
check(abs(valor_efectivo(ws) - 42300) < 0.01,
      "sin campo gastos: la fila muestra el conteo (registros viejos)")

# --- Caso real del usuario: ingresos 100, gastos 50 ---
ws = exportar({"fecha": "2026-10-27", "chofer": "X", "gastos": 50,
               "billetes": {"100": 1}, "total_billetes": 100})
check(abs(valor_efectivo(ws) - 50) < 0.01,
      "caso del pedido: 100 de ingresos − 50 de gastos = 50")

os.remove(os.path.join(tempfile.gettempdir(), "planilla_gastos_test.xlsx"))
print(f"\nTODAS LAS PRUEBAS DE GASTOS EN LA PLANILLA PASARON "
      f"({ok} verificaciones)")
