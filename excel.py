# -*- coding: utf-8 -*-
"""
Exportación de los movimientos de un período a un archivo Excel (.xlsx).

La plantilla arranca con dos recuadros por sección de pago (EFEC, TARJETA,
TRANS): uno con las garrafas con gas y otro con los envases sueltos, cada
uno con TOTAL GENERAL y control de cuadre. Solo aparecen los productos que
se vendieron en el período, en columnas 10 KG · 15 KG · 45 KG · ME · ECO.
Después detalla los movimientos por medio de pago: TRANSFERENCIAS,
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

# Columnas de cada movimiento. La hoja tiene 8 columnas de ancho fijo y cada
# campo del detalle ocupa 2 (para que el recuadro del resumen pueda usar
# columnas sueltas por producto sin ensanchar nada).
ENCABEZADOS = ["Nombre", "Carga", "N° Comprobante / Tarjeta", "Total"]
PARES_DETALLE = [(1, 2), (3, 4), (5, 6), (7, 8)]
N_COL = 8
ANCHOS = [20, 14, 14, 14, 14, 14, 13, 18]

# Secciones del resumen de unidades: (rótulo corto, medios que agrupa)
RESUMEN_SECCIONES = [
    ("EFEC", ["Efectivo"]),
    ("TARJETA", ["Tarjeta de débito", "Tarjeta de crédito"]),
    ("TRANS", ["Transferencia"]),
]

# Orden en que se muestran las columnas del recuadro
ORDEN_ROTULOS = {"10": 0, "15": 1, "45": 2, "ME": 3, "ECO": 4}


def _carga(v):
    """Detalle de la carga: '1 × Garrafa 10 kg + 1 × Garrafa 15 kg'."""
    if v.get("items"):
        return db.texto_items(v["items"]) or "—"
    producto = v.get("producto") or "Producto"
    return f"{v.get('cantidad', 0)} × {producto}"


def _filas_pago(movimientos, medio):
    """Filas del detalle para un medio de pago: UNA por cada cobro de ese
    medio. Así una venta mixta aparece en cada sección que utilizó, con el
    importe que le tocó a cada una (y los subtotales cierran exactos),
    siempre identificada con el número de ticket al que pertenece."""
    filas = []
    for v in movimientos:
        pagos = [p for p in (v.get("pagos") or []) if p["medio"] == medio]
        if not pagos and not v.get("pagos") and v.get("medio") == medio:
            pagos = [{"medio": medio, "importe": v["total"],
                      "comprobante": v.get("comprobante")}]
        for i, pg in enumerate(pagos):
            cliente = (v.get("cliente") or "").strip()
            numero = f"#{v['id']}"
            filas.append({
                "ticket": v["id"],
                "nombre": f"{numero} · {cliente}" if i == 0 and cliente
                          else numero,
                "cliente": cliente if i == 0 else "",
                "carga": _carga(v),
                "comprobante": pg.get("comprobante"),
                "total": float(pg["importe"]),
            })
    return filas


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
    # Cada venta (ticket) puede llevar varios productos: se recorren sus
    # ítems; si viniera en el formato viejo se usa la fila entera.
    for v in movimientos:
        for it in (v.get("items") or [v]):
            pid = it.get("producto_id")
            if pid is not None and pid not in nombres:
                orden.append(pid)
                nombres[pid] = it.get("producto") or f"Producto {pid}"

    garrafas, envases = [], []
    for pid in orden:
        item = (pid, nombres[pid])
        (envases if db.es_envase(nombres[pid]) else garrafas).append(item)
    return garrafas, envases


def _unidades_por_medio(movimientos):
    """{medio: {producto_id: unidades}} de todo el período.

    Las unidades de una venta MIXTA (varios medios de pago) se acreditan
    al MEDIO PRINCIPAL, el que aporta más dinero de esa venta; así los
    totales de unidades siempre cierran sin fracciones. El dinero sí se
    reparte exacto entre todos los medios (ver _dinero_por_medio).
    """
    datos = {}
    for v in movimientos:
        medio = v.get("medio") or db.medio_principal(v.get("pagos") or [])
        if not medio:
            continue
        celda = datos.setdefault(medio, {})
        for it in (v.get("items") or [v]):
            pid = it.get("producto_id")
            if pid is None:
                continue
            celda[pid] = celda.get(pid, 0) + int(it["cantidad"])
    return datos


def _familia_de(nombre):
    """'envases' si el producto es un envase suelto, si no 'garrafas'."""
    return "envases" if db.es_envase(nombre) else "garrafas"


def _dinero_por_medio(movimientos):
    """{(medio, familia): dinero cobrado}.

    El dinero de cada venta se reparte entre sus productos en la misma
    proporción de sus subtotales (una venta con garrafas y envases deja
    exacto el total de cada familia) y entre los medios de pago según lo
    que canceló cada uno (una venta mixta reparte su total entre los
    medios que la pagaron).
    """
    datos = {}
    for v in movimientos:
        items = v.get("items") or [v]
        pagos = v.get("pagos") or [
            {"medio": v.get("medio"), "importe": v["total"]}
        ]
        total = float(v.get("total") or 0)
        partes = {"garrafas": 0.0, "envases": 0.0}
        for it in items:
            monto = float(it.get("subtotal", it.get("total")) or 0)
            partes[_familia_de(it.get("producto"))] += monto
        if total <= 0:
            total = sum(float(p["importe"]) for p in pagos)
        for pg in pagos:
            importe = float(pg["importe"])
            for fam, monto in partes.items():
                if monto <= 0 or total <= 0:
                    continue
                clave = (pg["medio"], fam)
                datos[clave] = round(datos.get(clave, 0.0)
                                     + importe * (monto / total), 2)
    return datos


def _sumar_unidades(datos, medios):
    """Une en un solo mapa por producto las unidades de esos medios."""
    salida = {}
    for medio in medios:
        for pid, cantidad in datos.get(medio, {}).items():
            salida[pid] = salida.get(pid, 0) + cantidad
    return salida


def etiqueta_corta(nombre):
    """'Garrafa 10 kg' -> '10 KG'   |   'Envase ECO PROPANO' -> 'ECO'."""
    texto = str(nombre).strip()
    bajo = texto.lower()
    for prefijo in ("garrafa ", "envase "):
        if bajo.startswith(prefijo):
            texto = texto[len(prefijo):]
            break
    texto = " ".join(texto.split()).upper()
    texto = texto.replace("ECO PROPANO", "ECO").strip()
    return texto or str(nombre).upper()


def orden_recuadro(productos):
    """Columnas en el pedido 10 → 15 → 45 → ME → ECO y el resto al final."""
    return sorted(productos,
                  key=lambda p: ORDEN_ROTULOS.get(etiqueta_corta(p[1]), 50))


def _vendidos(producto_id, datos_medio):
    """True si ese producto tuvo al menos una unidad vendida en el período."""
    return any(mapa.get(producto_id, 0) > 0
               for mapa in datos_medio.values())


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
    tickets_vistos = set()          # tickets distintos que aparecen abajo

    def _fila_titulo(texto, fuente, relleno, alto=22, ancho=N_COL):
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
        for (col_ini, col_fin), texto_enc in zip(PARES_DETALLE, ENCABEZADOS):
            ws.merge_cells(start_row=fila, start_column=col_ini,
                           end_row=fila, end_column=col_fin)
            celda = ws.cell(row=fila, column=col_ini, value=texto_enc)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.alignment = centro
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(row=fila, column=col)
                celda.fill = relleno_enc
                celda.border = borde
        ws.row_dimensions[fila].height = 26
        fila += 1

    def _fila_detalle(valores, vacia=False):
        """Una fila del detalle: 4 campos, cada uno en 2 columnas."""
        nonlocal fila
        for i, ((col_ini, col_fin), valor) in enumerate(
                zip(PARES_DETALLE, valores)):
            ws.merge_cells(start_row=fila, start_column=col_ini,
                           end_row=fila, end_column=col_fin)
            celda = ws.cell(row=fila, column=col_ini, value=valor)
            if i == 3:
                if valor is not None:
                    celda.number_format = FORMATO_MONEDA
                celda.alignment = texto_der
            elif i == 2:
                celda.alignment = centro
            else:
                celda.alignment = texto
            if vacia:
                celda.font = Font(italic=True, color="999999")
            for col in range(col_ini, col_fin + 1):
                ws.cell(row=fila, column=col).border = borde
        fila += 1

    def _detalle(items, vacio_txt):
        nonlocal fila
        if not items:
            _fila_detalle(["—", vacio_txt, "—", None], vacia=True)
            return
        for v in items:
            comprobante = (v.get("comprobante") or "").strip() or "—"
            _fila_detalle([
                str(v.get("nombre") or v.get("cliente") or "—").strip() or "—",
                v.get("carga") or _carga(v),
                comprobante,
                float(v["total"]),
            ])

    def _subtotal(texto, monto):
        """Fila de subtotal: rótulo en A:F y el monto en G:H."""
        nonlocal fila
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                       end_column=6)
        celda_t = ws.cell(row=fila, column=1, value=texto)
        celda_t.font = Font(bold=True, size=11)
        celda_t.alignment = texto_der
        ws.merge_cells(start_row=fila, start_column=7, end_row=fila,
                       end_column=8)
        celda_v = ws.cell(row=fila, column=7, value=monto)
        celda_v.font = Font(bold=True, size=11)
        celda_v.number_format = FORMATO_MONEDA
        celda_v.alignment = texto_der
        for col in range(1, N_COL + 1):
            celda = ws.cell(row=fila, column=col)
            celda.fill = relleno_total
            celda.border = borde
        fila += 1

    # ---------------- Recuadros por sección de pago ----------------
    def _recuadro_enc(rotulos):
        """Encabezado del recuadro: [(texto, columna), ...]."""
        nonlocal fila
        for texto_enc, col in rotulos:
            celda = ws.cell(row=fila, column=col, value=texto_enc)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.alignment = centro
        for col in range(1, rotulos[-1][1] + 1):
            ws.cell(row=fila, column=col).fill = relleno_enc
            ws.cell(row=fila, column=col).border = borde
        ws.row_dimensions[fila].height = 26
        fila += 1

    def _recuadro_fila(rotulo, productos, mapa, dinero=0.0, *,
                       fuente=None, relleno=None):
        """Fila: rótulo | unidades por producto | unidades totales | $.

        `mapa` trae UNIDADES por producto (las de esa sección) y `dinero`
        es el efectivo/total cobrado con esos medios, que sale de los
        pagos y por eso siempre cierra exacto.
        """
        nonlocal fila
        fuente = fuente or Font(size=10)
        col_uni = 2 + len(productos)
        col_din = col_uni + 1

        celda_r = ws.cell(row=fila, column=1, value=rotulo)
        celda_r.font = fuente
        celda_r.alignment = texto

        for i, (pid, _nombre) in enumerate(productos):
            celda = ws.cell(row=fila, column=2 + i,
                            value=int(mapa.get(pid, 0)))
            celda.number_format = FORMATO_ENTERO
            celda.alignment = centro
            celda.font = fuente

        unidades = sum(int(mapa.get(pid, 0)) for pid, _ in productos)
        celda_u = ws.cell(row=fila, column=col_uni, value=int(unidades))
        celda_u.number_format = FORMATO_ENTERO
        celda_u.alignment = centro
        celda_u.font = Font(bold=True, size=11, color=AZUL)

        celda_d = ws.cell(row=fila, column=col_din, value=float(dinero))
        celda_d.number_format = FORMATO_MONEDA
        celda_d.alignment = texto_der
        celda_d.font = Font(bold=True, size=11)

        for col in range(1, col_din + 1):
            celda = ws.cell(row=fila, column=col)
            celda.border = borde
            if relleno is not None:
                celda.fill = relleno
        ws.row_dimensions[fila].height = 17
        fila += 1

    def _recuadro(titulo, productos, familia, aclaracion=None):
        """Recuadro de una familia (garrafas con gas / envases sueltos):
        Sección | una columna por producto | Unidades | Total $.

        Solo entran productos de esa familia con ventas; cada bloque
        cierra con su TOTAL GENERAL y los dos controles de cuadre. Las
        unidades van al medio principal de cada venta y el dinero sale de
        los pagos, repartido entre las familias en la proporción de sus
        subtotales.
        """
        nonlocal fila
        col_uni = 2 + len(productos)
        col_din = col_uni + 1

        secciones = [
            (rotulo, _sumar_unidades(datos_medio, medios),
             _dinero_seccion(medios, familia))
            for rotulo, medios in RESUMEN_SECCIONES
        ]
        mapa_total = _sumar_unidades(datos_medio, medios_periodo)
        dinero_total = _dinero_seccion(medios_periodo, familia)

        _fila_titulo(titulo, Font(bold=True, size=12, color="FFFFFF"),
                     relleno_seccion, ancho=col_din)
        if aclaracion:
            ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                           end_column=col_din)
            celda = ws.cell(row=fila, column=1, value=aclaracion)
            celda.font = Font(italic=True, size=9, color="555555")
            celda.alignment = texto
            for col in range(1, col_din + 1):
                ws.cell(row=fila, column=col).fill = relleno_total
                ws.cell(row=fila, column=col).border = borde
            ws.row_dimensions[fila].height = 16
            fila += 1

        _recuadro_enc([("Sección", 1)]
                      + [(etiqueta_corta(nombre), 2 + i)
                         for i, (_pid, nombre) in enumerate(productos)]
                      + [("Unidades", col_uni), ("Total $", col_din)])

        nombres_seccion, unidades_seccion, dinero_seccion = [], [], []
        for rotulo, mapa, dinero in secciones:
            _recuadro_fila(rotulo, productos, mapa, dinero)
            nombres_seccion.append(rotulo)
            unidades_seccion.append(sum(int(mapa.get(pid, 0))
                                        for pid, _ in productos))
            dinero_seccion.append(dinero)

        _recuadro_fila("TOTAL GENERAL", productos, mapa_total, dinero_total,
                       fuente=Font(bold=True, size=11),
                       relleno=relleno_total)
        total_unidades = sum(int(mapa_total.get(pid, 0))
                             for pid, _ in productos)

        _fila_control("CONTROL DE UNIDADES", nombres_seccion,
                      unidades_seccion, total_unidades, ancho=col_din)
        _fila_control("CONTROL DE DINERO", nombres_seccion,
                      dinero_seccion, dinero_total, ancho=col_din,
                      con_dinero=True)
        fila += 1

    def _fila_control(rotulo, secciones, valores, total, *,
                      con_dinero=False, ancho=N_COL):
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

        ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                       end_column=ancho - 1)
        celda = ws.cell(row=fila, column=1, value=f"{rotulo}: {expr}")
        celda.font = Font(bold=True, size=10)
        celda.alignment = texto
        estado = ws.cell(row=fila, column=ancho,
                         value="COINCIDE" if coincide else "REVISAR")
        estado.font = Font(bold=True, size=10,
                           color="1B7F3B" if coincide else "C0392B")
        estado.alignment = centro
        for col in range(1, ancho + 1):
            ws.cell(row=fila, column=col).fill = relleno_total
            ws.cell(row=fila, column=col).border = borde
        ws.row_dimensions[fila].height = 18
        fila += 1

    datos_medio = _unidades_por_medio(movimientos)
    dinero_medio = _dinero_por_medio(movimientos)
    # Todos los medios que recibieron dinero (y los que aportaron unidades)
    # en el período: así el TOTAL GENERAL cierra aunque aparezca un medio
    # fuera de las secciones armadas abajo.
    medios_periodo = sorted({m for (m, _f) in dinero_medio} | set(datos_medio))

    def _dinero_seccion(medios, familia):
        return round(sum(dinero_medio.get((m, familia), 0.0) for m in medios), 2)

    garrafas, envases = _productos_resumen(movimientos)
    # Solo los productos que se vendieron en el período, en el orden
    # pedido 10 → 15 → 45 → ME → ECO.
    garrafas = orden_recuadro([p for p in garrafas
                               if _vendidos(p[0], datos_medio)])
    envases = orden_recuadro([p for p in envases
                              if _vendidos(p[0], datos_medio)])

    _fila_titulo("RESUMEN DE VENTAS POR SECCIÓN DE PAGO",
                 Font(bold=True, size=13, color="FFFFFF"), relleno_enc,
                 alto=24)

    if not (garrafas or envases):
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila,
                       end_column=N_COL)
        celda = ws.cell(row=fila, column=1, value="Sin ventas en el período.")
        celda.font = Font(italic=True, size=11, color="999999")
        celda.alignment = texto
        fila += 2
    else:
        if garrafas:
            _recuadro("VENTA DE GARRAFAS (con gas)", garrafas, "garrafas",
                      aclaracion="Solo figuran las garrafas que se vendieron "
                                 "en el período.")
        if envases:
            _recuadro("VENTA DE ENVASES", envases, "envases",
                      aclaracion="Envases sueltos, sin gas: se venden y se "
                                 "devuelven aparte de las garrafas "
                                 "(10 kg, 15 kg, 45 kg, ME y ECO PROPANO). "
                                 "Nunca se suman con las garrafas con gas.")
    fila += 1

    # ---------------- Una sección por medio de pago ----------------
    for titulo, bloques in SECCIONES:
        # Título de la sección (p. ej. TARJETAS)
        _fila_titulo(titulo, Font(bold=True, size=12, color="FFFFFF"),
                     relleno_seccion)

        subtotal_seccion = 0.0
        for i_bloque, (subtitulo, medio) in enumerate(bloques):
            # Una fila por cada cobro de ese medio: una venta pagada con
            # dos medios aparece en las dos secciones, cada una con el
            # importe que le tocó (nunca se duplica el total).
            items = _filas_pago(movimientos, medio)
            tickets_vistos.update(v["ticket"] for v in items)

            # Dentro de la sección, cada medio con su propio bloque
            if len(bloques) > 1:
                _fila_titulo(subtitulo, Font(bold=True, size=11, color="FFFFFF"),
                             relleno_bloque, alto=18)
            _encabezados()
            _detalle(items, f"Sin movimientos de {subtitulo.lower()} "
                            f"en el período.")

            subtotal = sum(float(v["total"]) for v in items)
            subtotal_seccion += subtotal
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
            ws.cell(row=fila - 1, column=7).font = Font(bold=True, size=12)
        fila += 1

    # Una venta = una operación: se cuentan tickets, no filas de cobro.
    cantidad_total = len(tickets_vistos)

    # ---------------- Total general ----------------
    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
    celda_t = ws.cell(row=fila, column=1, value="TOTAL GENERAL")
    celda_t.font = Font(bold=True, size=13)
    celda_t.alignment = texto_der
    for col in range(1, 7):
        ws.cell(row=fila, column=col).fill = relleno_enc
    ws.merge_cells(start_row=fila, start_column=7, end_row=fila, end_column=8)
    celda_v = ws.cell(row=fila, column=7, value=total_general)
    celda_v.font = Font(bold=True, size=13, color=AZUL)
    celda_v.number_format = FORMATO_MONEDA
    celda_v.alignment = texto_der
    celda_v.fill = relleno_enc
    for col in range(7, N_COL + 1):
        ws.cell(row=fila, column=col).fill = relleno_enc
    ws.row_dimensions[fila].height = 22
    fila += 1

    ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
    celda_t = ws.cell(row=fila, column=1, value="Cantidad de operaciones:")
    celda_t.font = Font(bold=True, size=10)
    celda_t.alignment = texto_der
    ws.merge_cells(start_row=fila, start_column=7, end_row=fila, end_column=8)
    celda_v = ws.cell(row=fila, column=7, value=cantidad_total)
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
    ws.print_area = f"A1:{get_column_letter(N_COL)}{ultima_fila}"
    ws.freeze_panes = "A5"

    wb.save(destino)
    return cantidad_total, total_general


def datetime_texto():
    """Fecha y hora de generación del archivo."""
    return datetime.now().strftime("%d/%m/%Y %H:%M")
