# -*- coding: utf-8 -*-
"""
Exportación de los movimientos de un período a un archivo Excel (.xlsx).

La plantilla queda organizada por medio de pago: TRANSFERENCIAS, TARJETAS
(con sus dos bloques: Tarjeta de débito y Tarjeta de crédito) y
DINERO / EFECTIVO, y configurada para imprimir directamente en hoja A4
horizontal, ajustada al ancho de la página.
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

import database as db
from util import fecha_corta

AZUL = "01ADEF"                      # color de marca
GRIS_CLARO = "F2F4F7"
FORMATO_MONEDA = '"$"#,##0'
FORMATO_ENTERO = "#,##0"

# Secciones del reporte: (título de la sección, bloques [(subtítulo, medio)])
# El bloque "TARJETAS" agrupa débito y crédito con su discriminación.
SECCIONES = [
    ("TRANSFERENCIAS", [("Transferencia", "Transferencia")]),
    ("TARJETAS", [("TARJETA DE DÉBITO", "Tarjeta de débito"),
                  ("TARJETA DE CRÉDITO", "Tarjeta de crédito")]),
    ("DINERO / EFECTIVO", [("Efectivo", "Efectivo")]),
]

# Columnas de cada movimiento
ENCABEZADOS = ["Nombre", "Carga", "N° Comprobante / Tarjeta", "Total"]
ANCHOS = [30, 38, 28, 16]


def _carga(v):
    """Detalle de la carga: '3 × Garrafa 10 kg'."""
    producto = v.get("producto") or "Producto"
    return f"{v['cantidad']} × {producto}"


def exportar_movimientos(desde, hasta, destino):
    """
    Genera un .xlsx con TODOS los movimientos del rango [desde, hasta]
    (fechas ISO), separados por medio de pago, listo para imprimir en
    A4 horizontal.

    Devuelve (cantidad_de_movimientos, monto_total).
    """
    movimientos = db.ventas_rango(desde, hasta)

    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"

    # ---------------- Encabezado del reporte ----------------
    fila = 1
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    celda = ws.cell(row=fila, column=1, value="MOVIMIENTOS DE CAJA")
    celda.font = Font(bold=True, size=16, color=AZUL)
    celda.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[fila].height = 24
    fila += 1

    rango_txt = (("Del " + fecha_corta(desde)) if desde else "") + \
                ((" al " + fecha_corta(hasta)) if hasta else "")
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    celda = ws.cell(row=fila, column=1, value=rango_txt.strip())
    celda.font = Font(italic=True, color="666666")
    celda.alignment = Alignment(horizontal="center")
    fila += 1

    u = db.usuario_sesion() or {}
    generado = datetime_texto() + \
               (f"  —  Exportado por: {u.get('usuario', '—')}" if u else "")
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
    celda = ws.cell(row=fila, column=1, value=generado)
    celda.font = Font(italic=True, size=9, color="999999")
    celda.alignment = Alignment(horizontal="center")
    fila += 2

    # ---------------- Estilos reutilizables ----------------
    lado = Side(style="thin", color="BFBFBF")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)
    relleno_enc = PatternFill(patternType="solid", fgColor=AZUL)
    relleno_seccion = PatternFill(patternType="solid", fgColor="1F2937")
    relleno_bloque = PatternFill(patternType="solid", fgColor="3B4A5E")
    relleno_total = PatternFill(patternType="solid", fgColor=GRIS_CLARO)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    texto = Alignment(horizontal="left", vertical="center")
    texto_der = Alignment(horizontal="right", vertical="center")

    total_general = 0.0
    cantidad_total = 0

    def _fila_titulo(texto, fuente, relleno, alto=22, ancho=4):
        """Fila de título (sección o bloque) que ocupa todo el ancho."""
        nonlocal fila
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                       end_column=ancho)
        celda = ws.cell(row=fila, column=1, value=texto)
        celda.font = fuente
        celda.alignment = Alignment(horizontal="left", vertical="center",
                                    indent=1)
        for col in range(1, ancho + 1):
            ws.cell(row=fila, column=col).fill = relleno
        ws.row_dimensions[fila].height = alto
        fila += 1

    def _encabezados():
        nonlocal fila
        for col, texto_enc in enumerate(ENCABEZADOS, start=1):
            celda = ws.cell(row=fila, column=col, value=texto_enc)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = relleno_enc
            celda.alignment = centro
            celda.border = borde
        ws.row_dimensions[fila].height = 26
        fila += 1

    def _detalle(items, vacio_txt):
        nonlocal fila
        if not items:
            valores = ["—", vacio_txt, "—", None]
            for col, valor in enumerate(valores, start=1):
                celda = ws.cell(row=fila, column=col, value=valor)
                celda.border = borde
                celda.font = Font(italic=True, color="999999")
                celda.alignment = texto if col in (1, 2) else centro
            fila += 1
            return
        for v in items:
            comprobante = (v.get("comprobante") or "").strip() or "—"
            valores = [
                (v.get("cliente") or "").strip() or "—",
                _carga(v),
                comprobante,
                float(v["total"]),
            ]
            for col, valor in enumerate(valores, start=1):
                celda = ws.cell(row=fila, column=col, value=valor)
                celda.border = borde
                if col == 4:
                    celda.number_format = FORMATO_MONEDA
                    celda.alignment = texto_der
                elif col == 3:
                    celda.alignment = centro
                else:
                    celda.alignment = texto
            fila += 1

    def _subtotal(texto, monto):
        """Fila de subtotal (1 a 3 columnas de rótulo + monto en la 4)."""
        nonlocal fila
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
        celda_t = ws.cell(row=fila, column=1, value=texto)
        celda_t.font = Font(bold=True, size=11)
        celda_t.alignment = texto_der
        for col in range(1, 4):
            ws.cell(row=fila, column=col).fill = relleno_total
            ws.cell(row=fila, column=col).border = borde
        celda_v = ws.cell(row=fila, column=4, value=monto)
        celda_v.font = Font(bold=True, size=11)
        celda_v.number_format = FORMATO_MONEDA
        celda_v.alignment = texto_der
        celda_v.fill = relleno_total
        celda_v.border = borde
        fila += 1

    # ---------------- Una sección por medio de pago ----------------
    for titulo, bloques in SECCIONES:
        # Título de la sección (p. ej. TARJETAS)
        _fila_titulo(titulo, Font(bold=True, size=12, color="FFFFFF"),
                     relleno_seccion)

        subtotal_seccion = 0.0
        for i_bloque, (subtitulo, medio) in enumerate(bloques):
            items = [v for v in movimientos if v["medio"] == medio]

            # Dentro de la sección, cada medio con su propio bloque
            if len(bloques) > 1:
                _fila_titulo(subtitulo, Font(bold=True, size=11, color="FFFFFF"),
                             relleno_bloque, alto=18)
            _encabezados()
            _detalle(items, f"Sin movimientos de {subtitulo.lower()} "
                            f"en el período.")

            subtotal = sum(float(v["total"]) for v in items)
            subtotal_seccion += subtotal
            cantidad_total += len(items)
            rotulo = (f"Total {medio}" if len(bloques) > 1
                      else f"Total {titulo}")
            _subtotal(rotulo, subtotal)
            # Un espacio en blanco entre bloques (no después del último)
            if i_bloque < len(bloques) - 1:
                fila += 1

        # Total de la sección (suma de sus bloques discriminados)
        total_general += subtotal_seccion
        if len(bloques) > 1:
            _subtotal(f"TOTAL {titulo}", subtotal_seccion)
            ws.cell(row=fila - 1, column=1).font = Font(bold=True, size=12)
            ws.cell(row=fila - 1, column=4).font = Font(bold=True, size=12)
        fila += 1

    # ---------------- Total general ----------------
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
    celda_t = ws.cell(row=fila, column=1, value="TOTAL GENERAL")
    celda_t.font = Font(bold=True, size=13)
    celda_t.alignment = texto_der
    for col in range(1, 4):
        ws.cell(row=fila, column=col).fill = relleno_enc
    celda_v = ws.cell(row=fila, column=4, value=total_general)
    celda_v.font = Font(bold=True, size=13, color=AZUL)
    celda_v.number_format = FORMATO_MONEDA
    celda_v.alignment = texto_der
    celda_v.fill = relleno_enc
    ws.row_dimensions[fila].height = 22
    fila += 1

    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
    celda_t = ws.cell(row=fila, column=1, value="Cantidad de movimientos:")
    celda_t.font = Font(bold=True, size=10)
    celda_t.alignment = texto_der
    celda_v = ws.cell(row=fila, column=4, value=cantidad_total)
    celda_v.font = Font(bold=True, size=10, color=AZUL)
    celda_v.number_format = FORMATO_ENTERO
    celda_v.alignment = texto_der
    ultima_fila = fila

    # ---------------- Anchos de columna ----------------
    for i, ancho in enumerate(ANCHOS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    # ---------------- Impresión: A4 horizontal, ajustado al ancho ----------------
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5,
                                  header=0.2, footer=0.2)
    ws.print_options.horizontalCentered = True
    ws.print_title_rows = "1:3"          # encabezados que se repiten en cada página
    ws.print_area = f"A1:D{ultima_fila}"
    ws.freeze_panes = "A5"

    wb.save(destino)
    return cantidad_total, total_general


def datetime_texto():
    """Fecha y hora de generación del archivo."""
    return datetime.now().strftime("%d/%m/%Y %H:%M")
