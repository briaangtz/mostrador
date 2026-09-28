# -*- coding: utf-8 -*-
"""
Exportación de los movimientos de un período a un archivo Excel (.xlsx).

La plantilla arranca con un resumen de unidades vendidas por sección
(EFEC, TARJETA, TRANS) con el TOTAL GENERAL y un control de cuadre, y
después detalla los movimientos por medio de pago: TRANSFERENCIAS,
TARJETAS (con sus dos bloques: Tarjeta de débito y Tarjeta de crédito)
y DINERO / EFECTIVO, configurada para imprimir directamente en hoja
A4 horizontal, ajustada al ancho de la página.
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

import database as db
from util import fecha_corta, money

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

# Secciones del resumen de unidades: (rótulo corto, medios que agrupa)
RESUMEN_SECCIONES = [
    ("EFEC", ["Efectivo"]),
    ("TARJETA", ["Tarjeta de débito", "Tarjeta de crédito"]),
    ("TRANS", ["Transferencia"]),
]

ROTULO_GARRAFAS = "TOTAL DE ENVASES"            # solo garrafas con gas
ROTULO_ENVASES = "TOTAL DE ENVASES SUELTOS"     # envases vendidos aparte


def _carga(v):
    """Detalle de la carga: '3 × Garrafa 10 kg'."""
    producto = v.get("producto") or "Producto"
    return f"{v['cantidad']} × {producto}"


# ---------------------------------------------------------------------------
# Resumen de unidades por sección
# ---------------------------------------------------------------------------

def _productos_resumen(movimientos):
    """
    Productos que aparecen en el resumen, como (id, nombre):
    primero las garrafas con gas y después los envases sueltos.
    Incluye productos dados de baja que igual tuvieron ventas.
    """
    orden, nombres = [], {}
    for p in db.productos():
        orden.append(p["id"])
        nombres[p["id"]] = p["nombre"]
    for v in movimientos:
        pid = v.get("producto_id")
        if pid is not None and pid not in nombres:
            orden.append(pid)
            nombres[pid] = v.get("producto") or f"Producto {pid}"

    garrafas, envases = [], []
    for pid in orden:
        item = (pid, nombres[pid])
        (envases if db.es_envase(nombres[pid]) else garrafas).append(item)
    return garrafas, envases


def _unidades_por_medio(movimientos):
    """{medio: {producto_id: [cantidad, dinero]}} con todo lo del período."""
    datos = {}
    for v in movimientos:
        celda = datos.setdefault(v["medio"], {})
        cantidad, dinero = celda.get(v["producto_id"], (0, 0.0))
        celda[v["producto_id"]] = (cantidad + int(v["cantidad"]),
                                   dinero + float(v["total"]))
    return datos


def _sumar_medios(datos, medios):
    """Une en un solo mapa por producto todos los medios de una sección."""
    salida = {}
    for medio in medios:
        for pid, (cantidad, dinero) in datos.get(medio, {}).items():
            c, d = salida.get(pid, (0, 0.0))
            salida[pid] = (c + cantidad, d + dinero)
    return salida


def _totales(mapa, productos):
    """(cantidad, dinero) de una lista de productos dentro de un mapa."""
    cantidad, dinero = 0, 0.0
    for pid, _ in productos:
        c, d = mapa.get(pid, (0, 0.0))
        cantidad += c
        dinero += d
    return cantidad, dinero


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

    # ---------------- Resumen de unidades por sección ----------------
    def _enc_resumen():
        """Encabezado del resumen: Producto (A:B) | Unidades | Total $."""
        nonlocal fila
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=2)
        for col, rotulo in ((1, "Producto"), (3, "Unidades"), (4, "Total $")):
            celda = ws.cell(row=fila, column=col, value=rotulo)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.alignment = centro
        for col in range(1, 5):
            ws.cell(row=fila, column=col).fill = relleno_enc
            ws.cell(row=fila, column=col).border = borde
        ws.row_dimensions[fila].height = 26
        fila += 1

    def _fila_resumen(rotulo, cantidad, dinero, *, fuente=None, relleno=None,
                      mostrar_unidades=True, mostrar_dinero=True):
        """Fila del resumen: rótulo en A:B, unidades en C, dinero en D."""
        nonlocal fila
        fuente = fuente or Font(size=10)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=2)
        celda_r = ws.cell(row=fila, column=1, value=rotulo)
        celda_r.font = fuente
        celda_r.alignment = texto

        celda_c = ws.cell(row=fila, column=3)
        if mostrar_unidades:
            celda_c.value = int(cantidad)
            celda_c.number_format = FORMATO_ENTERO
            celda_c.alignment = centro
        celda_c.font = fuente

        celda_d = ws.cell(row=fila, column=4)
        if mostrar_dinero:
            celda_d.value = float(dinero)
            celda_d.number_format = FORMATO_MONEDA
        celda_d.alignment = texto_der
        celda_d.font = fuente

        for col in range(1, 5):
            celda = ws.cell(row=fila, column=col)
            celda.border = borde
            if relleno is not None:
                celda.fill = relleno
        ws.row_dimensions[fila].height = 17
        fila += 1

    def _bloque_resumen(titulo, mapa):
        """Una sección del resumen: garrafas, envases sueltos y sus totales."""
        _fila_titulo(titulo, Font(bold=True, size=12, color="FFFFFF"),
                     relleno_seccion)
        _enc_resumen()
        for pid, nombre in garrafas:
            c, d = mapa.get(pid, (0, 0.0))
            _fila_resumen(nombre, c, d)

        c, d = _totales(mapa, garrafas)
        _fila_resumen(ROTULO_GARRAFAS, c, d, fuente=Font(bold=True, size=11),
                      relleno=relleno_total)

        if envases:
            for pid, nombre in envases:
                c, d = mapa.get(pid, (0, 0.0))
                _fila_resumen(nombre, c, d)
            c, d = _totales(mapa, envases)
            _fila_resumen(ROTULO_ENVASES, c, d, fuente=Font(bold=True, size=11),
                          relleno=relleno_total)

        unidades, dinero = _totales(mapa, garrafas + envases)
        _fila_resumen("TOTAL DE UNIDADES", unidades, None,
                      fuente=Font(bold=True, size=11), relleno=relleno_total,
                      mostrar_dinero=False)
        _fila_resumen("TOTAL DE DINERO", None, dinero,
                      fuente=Font(bold=True, size=11), relleno=relleno_total,
                      mostrar_unidades=False)

    def _fila_control(rotulo, secciones, valores, total, *, con_dinero=False):
        """Control: 'EFEC(...) + TARJETA(...) + TRANS(...) = total'."""
        nonlocal fila
        if con_dinero:
            partes = [f"{r}({money(v)})" for r, v in zip(secciones, valores)]
            expr = " + ".join(partes) + " = " + money(total)
            coincide = abs(sum(valores) - float(total)) < 0.01
        else:
            partes = [f"{r}({int(v)})" for r, v in zip(secciones, valores)]
            expr = " + ".join(partes) + " = " + str(int(total))
            coincide = abs(sum(valores) - int(total)) < 1e-6

        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
        celda = ws.cell(row=fila, column=1, value=f"{rotulo}: {expr}")
        celda.font = Font(bold=True, size=10)
        celda.alignment = texto
        estado = ws.cell(row=fila, column=4,
                         value="COINCIDE" if coincide else "REVISAR")
        estado.font = Font(bold=True, size=10,
                           color="1B7F3B" if coincide else "C0392B")
        estado.alignment = centro
        for col in range(1, 5):
            ws.cell(row=fila, column=col).fill = relleno_total
            ws.cell(row=fila, column=col).border = borde
        ws.row_dimensions[fila].height = 18
        fila += 1

    datos_medio = _unidades_por_medio(movimientos)
    garrafas, envases = _productos_resumen(movimientos)

    _fila_titulo("GARRAFAS Y ENVASES VENDIDOS POR SECCIÓN",
                 Font(bold=True, size=13, color="FFFFFF"), relleno_enc, alto=24)

    secciones_resumen = [(rotulo, _sumar_medios(datos_medio, medios))
                         for rotulo, medios in RESUMEN_SECCIONES]
    unidades_seccion, dinero_seccion = [], []
    for rotulo, mapa in secciones_resumen:
        _bloque_resumen(rotulo, mapa)
        c, d = _totales(mapa, garrafas + envases)
        unidades_seccion.append(c)
        dinero_seccion.append(d)
        fila += 1

    # Total general: se calcula con TODOS los medios que hubo en el período,
    # así si alguno quedara fuera de las secciones el control lo marca.
    mapa_total = _sumar_medios(datos_medio, sorted(datos_medio))
    _bloque_resumen("TOTAL GENERAL DE GARRAFAS Y ENVASES", mapa_total)
    total_unidades, total_dinero = _totales(mapa_total, garrafas + envases)

    nombres_seccion = [rotulo for rotulo, _ in secciones_resumen]
    _fila_control("CONTROL DE UNIDADES", nombres_seccion, unidades_seccion,
                  total_unidades)
    _fila_control("CONTROL DE DINERO", nombres_seccion, dinero_seccion,
                  total_dinero, con_dinero=True)
    fila += 2

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
