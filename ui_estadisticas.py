# -*- coding: utf-8 -*-
"""Panel de Estadísticas: ventas, medios de pago, evolución y cierres."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta

import database as db
import estilos as st
import excel
from util import money, fecha_corta, fecha_a_iso, fecha_larga

MAX_DIAS_GRAFICO = 21


class EstadisticasPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._stats = None
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # Contenido con scroll vertical
        marco_exterior = tk.Frame(self, bg=st.FONDO)
        marco_exterior.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(marco_exterior, bg=st.FONDO, highlightthickness=0)
        self.canvas_scroll = self.canvas    # lo usa App._rueda_global
        scroll = ttk.Scrollbar(marco_exterior, orient="vertical",
                               command=self.canvas.yview)
        self.contenido = tk.Frame(self.canvas, bg=st.FONDO)
        self.contenido.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._ventana_canvas = self.canvas.create_window(
            (0, 0), window=self.contenido, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._ventana_canvas, width=e.width),
        )
        for evento in ("<MouseWheel>",):
            self.contenido.bind(evento, self._scroll_mouse)

        cont = self.contenido

        # Cabecera
        cab = tk.Frame(cont, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(cab, text="ESTADÍSTICAS", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        self.lbl_periodo = tk.Label(cab, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                    font=(st.FUENTE, 11))
        self.lbl_periodo.pack(anchor="w")

        # ---------------- Filtros por fecha ----------------
        filtros = st.labelframe(cont, " PERÍODO DE CONSULTA ", padx=14, pady=10)
        filtros.pack(fill="x", padx=24, pady=(12, 0))

        fila_f = tk.Frame(filtros, bg=st.FONDO)
        fila_f.pack(fill="x")

        def campo_fecha(texto):
            c = tk.Frame(fila_f, bg=st.FONDO)
            tk.Label(c, text=texto, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar()
            tk.Entry(c, textvariable=var, width=12, font=(st.FUENTE, 11),
                     justify="center", relief="solid", bd=1).pack(pady=(3, 0),
                                                                  ipady=3)
            return var, c

        self.var_desde, f1 = campo_fecha("DESDE (dd/mm/aaaa)")
        self.var_hasta, f2 = campo_fecha("HASTA (dd/mm/aaaa)")
        f1.pack(side="left")
        f2.pack(side="left", padx=(14, 0))

        c_botones = tk.Frame(fila_f, bg=st.FONDO)
        c_botones.pack(side="left", padx=(20, 0), anchor="s")
        tk.Label(c_botones, text="", bg=st.FONDO).pack()
        fila_botones = tk.Frame(c_botones, bg=st.FONDO)
        fila_botones.pack(anchor="w", pady=(16, 0))

        self._btn(fila_botones, "Hoy", lambda: self._preset("hoy")).pack(
            side="left", padx=(0, 6))
        self._btn(fila_botones, "Últimos 7 días",
                  lambda: self._preset("semana")).pack(side="left", padx=(0, 6))
        self._btn(fila_botones, "Este mes",
                  lambda: self._preset("mes")).pack(side="left", padx=(0, 6))
        self._btn(fila_botones, "Todo", lambda: self._preset("todo")).pack(
            side="left", padx=(0, 6))
        self._btn(fila_botones, "Actualizar", self._aplicar_fechas,
                  color=st.ACENTO).pack(side="left")

        c_excel = tk.Frame(fila_f, bg=st.FONDO)
        c_excel.pack(side="right", anchor="s")
        tk.Label(c_excel, text="", bg=st.FONDO).pack()
        btn_excel = tk.Button(
            c_excel, text="EXPORTAR",
            command=self._exportar_excel, relief="flat", bg=st.VERDE,
            fg="#ffffff", font=(st.FUENTE, 10, "bold"), padx=14, pady=10,
            cursor="hand2",
        )
        btn_excel.pack(anchor="e", pady=(16, 0))

        # ---------------- Tarjetas ----------------
        marco_cards = tk.Frame(cont, bg=st.FONDO)
        marco_cards.pack(fill="x", padx=24, pady=(14, 0))
        for c in range(4):
            marco_cards.columnconfigure(c, weight=1)

        definiciones = [
            ("Total de ventas", "ventas", 1),
            ("Garrafas vendidas", "garrafas", 1),
            ("Total recaudado", "recaudado", 1),
            ("Ventas promedio", "promedio", 1),
            ("Efectivo", "efectivo", 1),
            ("Transferencias", "transferencias", 1),
            ("Tarjetas", "tarjetas", 2),
            ("Transferencias (cantidad)", "n_transferencias", 1),
            ("Días con ventas", "dias", 1),
            ("Cierres en el período", "cierres", 1),
            ("Mayor venta del día", "max", 1),
        ]
        self.cards = {}
        self.cards_detalle = {}
        fila, col = 0, 0
        for titulo, clave, span in definiciones:
            if col + span > 4:
                fila, col = fila + 1, 0
            celda = tk.Frame(marco_cards, bg=st.FONDO)
            celda.grid(row=fila, column=col, columnspan=span,
                       sticky="nsew", padx=6, pady=6)
            frame, lbl = st.tarjeta(celda, titulo, ancho_chico=True)
            frame.pack(fill="both", expand=True)
            self.cards[clave] = lbl
            self.cards_detalle[clave] = frame.lbl_detalle
            col += span
        self.cards["recaudado"].config(fg=st.VERDE_OSCURO)

        # ---------------- Producto + evolución ----------------
        medio = tk.Frame(cont, bg=st.FONDO)
        medio.pack(fill="x", padx=24, pady=(14, 0))
        medio.columnconfigure(0, weight=1)
        medio.columnconfigure(1, weight=1)
        medio.rowconfigure(0, weight=1)

        izq = st.labelframe(medio, " VENTAS POR PRODUCTO ", padx=10, pady=10)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.tree_productos = ttk.Treeview(
            izq, columns=("producto", "garrafas", "total"), show="headings",
            height=5)
        self.tree_productos.heading("producto", text="Producto")
        self.tree_productos.heading("garrafas", text="Garrafas")
        self.tree_productos.heading("total", text="Total")
        self.tree_productos.column("producto", width=180, anchor="w")
        self.tree_productos.column("garrafas", width=90, anchor="center")
        self.tree_productos.column("total", width=130, anchor="e")
        self.tree_productos.pack(fill="both", expand=True)

        der = st.labelframe(medio, " EVOLUCIÓN DE VENTAS POR DÍA ", padx=10, pady=10)
        der.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.canvas_grafico = tk.Canvas(der, bg=st.TARJETA, highlightthickness=0,
                                        height=170)
        self.canvas_grafico.pack(fill="both", expand=True)
        self.lbl_grafico = tk.Label(der, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                    font=(st.FUENTE, 9), anchor="w")

        # ---------------- Cierres ----------------
        cierres_frame = st.labelframe(cont, " RESUMEN DE CIERRES DE CAJA ",
                                      padx=10, pady=10)
        cierres_frame.pack(fill="x", padx=24, pady=(14, 24))

        columnas = ("fecha", "vendido", "efectivo", "transferencia", "tarjetas",
                    "diferencia", "estado")
        self.tree_cierres = ttk.Treeview(cierres_frame, columns=columnas,
                                         show="headings", height=4)
        encabezados = [
            ("fecha", "Fecha", 92, "center"),
            ("vendido", "Total vendido", 122, "e"),
            ("efectivo", "Efectivo", 112, "e"),
            ("transferencia", "Transferencia", 120, "e"),
            ("tarjetas", "Tarjetas", 145, "e"),
            ("diferencia", "Diferencia", 104, "e"),
            ("estado", "Estado", 100, "center"),
        ]
        for clave, texto, ancho, alinear in encabezados:
            self.tree_cierres.heading(clave, text=texto)
            self.tree_cierres.column(clave, width=ancho, anchor=alinear)
        self.tree_cierres.pack(fill="x")

    def _btn(self, parent, texto, comando, color="#e5eaf1"):
        return tk.Button(parent, text=texto, command=comando, relief="flat",
                         bg=color,
                         fg="#ffffff" if color != "#e5eaf1" else st.TEXTO,
                         font=(st.FUENTE, 9, "bold"), padx=10, pady=6,
                         cursor="hand2")

    def _scroll_mouse(self, evento):
        self.canvas.yview_scroll(int(-evento.delta / 120), "units")

    # ------------------------------------------------------------- acciones
    def _rango_actual(self):
        desde = fecha_a_iso(self.var_desde.get())
        hasta = fecha_a_iso(self.var_hasta.get())
        return desde, hasta

    def _fechas_invalidas(self):
        messagebox.showwarning(
            "Fechas inválidas",
            "Ingresá fechas válidas con el formato dd/mm/aaaa "
            "(ejemplo: 01/09/2026).",
            parent=self,
        )

    def _preset(self, tipo):
        hoy = date.today()
        if tipo == "hoy":
            inicio = hoy
        elif tipo == "semana":
            inicio = hoy - timedelta(days=6)
        elif tipo == "mes":
            inicio = hoy.replace(day=1)
        elif tipo == "todo":
            cajas = db.todas_las_cajas()
            if not cajas:
                inicio = hoy
            else:
                minima = min(c["fecha"] for c in cajas)
                inicio = date.fromisoformat(minima)
        else:
            return
        self.var_desde.set(inicio.strftime("%d/%m/%Y"))
        self.var_hasta.set(hoy.strftime("%d/%m/%Y"))
        self._actualizar()

    def _aplicar_fechas(self):
        desde, hasta = self._rango_actual()
        if not desde or not hasta:
            self._fechas_invalidas()
            return
        if desde > hasta:
            desde, hasta = hasta, desde
            self.var_desde.set(fecha_corta(desde))
            self.var_hasta.set(fecha_corta(hasta))
        self._actualizar()

    def _exportar_excel(self):
        if not db.puede("exportar_excel"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no tiene permiso para exportar a "
                                 "Excel.", parent=self)
            return
        desde, hasta = self._rango_actual()
        if not desde or not hasta:
            self._fechas_invalidas()
            return

        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar movimientos a Excel",
            defaultextension=".xlsx",
            initialfile=f"movimientos_{fecha_corta(desde).replace('/', '-')}_{fecha_corta(hasta).replace('/', '-')}.xlsx",
            filetypes=[("Archivo de Excel", "*.xlsx")],
        )
        if not destino:
            return
        try:
            cantidad, monto = excel.exportar_movimientos(desde, hasta, destino)
        except Exception as exc:
            messagebox.showerror("Error al exportar",
                                 f"No se pudo generar el archivo:\n{exc}",
                                 parent=self)
            return
        db.log_actividad(
            "Exportación a Excel",
            f"Movimientos del {fecha_corta(desde)} al {fecha_corta(hasta)} — "
            f"{cantidad} movimientos — {money(monto)}",
        )
        messagebox.showinfo(
            "Exportación finalizada",
            f"Archivo generado:\n{destino}\n\n"
            f"Movimientos incluidos: {cantidad}\n"
            f"Total general: {money(monto)}\n\n"
            f"Período: del {fecha_corta(desde)} al {fecha_corta(hasta)}\n\n"
            "El archivo ya viene configurado para imprimir en hoja "
            "A4 horizontal: abrilo y presioná Imprimir.",
            parent=self,
        )

    # ------------------------------------------------------------- refresco
    def refresh(self):
        hoy = date.today()
        if not self.var_desde.get().strip():
            cajas = db.todas_las_cajas()
            inicio = (date.fromisoformat(min(c["fecha"] for c in cajas))
                      if cajas else hoy)
            self.var_desde.set(inicio.strftime("%d/%m/%Y"))
            self.var_hasta.set(hoy.strftime("%d/%m/%Y"))
        self._actualizar()

    def _actualizar(self):
        desde, hasta = self._rango_actual()
        if not desde or not hasta:
            return

        s = db.estadisticas(desde, hasta)
        self._stats = s
        self.lbl_periodo.config(
            text=f"Período: del {fecha_larga(desde)} al {fecha_larga(hasta)}"
        )

        promedio = (s["total_vendido"] / s["cantidad_ventas"]) if s["cantidad_ventas"] else 0
        maximo = max((v["total"] for v in db.ventas_rango(desde, hasta)), default=0)

        self.cards["ventas"].config(text=str(s["cantidad_ventas"]))
        self.cards["garrafas"].config(text=str(s["total_garrafas"]))
        self.cards["recaudado"].config(text=money(s["total_vendido"]))
        self.cards["promedio"].config(text=money(promedio))
        self.cards["efectivo"].config(text=money(s["efectivo"]))
        self.cards["transferencias"].config(text=money(s["transferencias"]))
        self.cards["tarjetas"].config(text=money(s["debito"] + s["credito"]))
        self.cards_detalle["tarjetas"].config(
            text=f"Débito {money(s['debito'])}  •  Crédito {money(s['credito'])}"
        )
        self.cards["n_transferencias"].config(text=str(s["n_transferencias"]))
        self.cards["dias"].config(text=str(s["dias_con_ventas"]))
        self.cards["cierres"].config(text=str(len(s["cierres"])))
        self.cards["max"].config(text=money(maximo))

        # Ventas por producto
        self.tree_productos.delete(*self.tree_productos.get_children())
        if not s["por_producto"]:
            self.tree_productos.insert("", "end",
                                       values=("Sin ventas en el período", "", ""))
        else:
            for pid, info in sorted(s["por_producto"].items(),
                                    key=lambda x: -x[1]["total"]):
                self.tree_productos.insert("", "end", values=(
                    info["nombre"], info["cantidad"], money(info["total"]),
                ))

        # Evolución diaria
        self._dibujar_grafico(s["evolucion"])

        # Cierres
        self.tree_cierres.delete(*self.tree_cierres.get_children())
        for c in s["cierres"]:
            self.tree_cierres.insert("", "end", values=(
                fecha_corta(c["fecha"]),
                money(c["total_vendido"]),
                money(c["efectivo_contado"]),
                money(c["transferencias"]),
                money(c["debito"] + c["credito"]),
                money(c["diferencia"]),
                c["estado"],
            ))
            etiqueta = ("faltante" if c["estado"] == "Faltante" else
                        "sobrante" if c["estado"] == "Sobrante" else "cuadrada")
            color = (st.ROJO if etiqueta == "faltante" else
                     st.AMBAR if etiqueta == "sobrante" else st.VERDE_OSCURO)
            self.tree_cierres.tag_configure(etiqueta, foreground=color)
            self.tree_cierres.item(self.tree_cierres.get_children()[-1],
                                   tags=(etiqueta,))

    def _dibujar_grafico(self, evolucion):
        lienzo = self.canvas_grafico
        lienzo.delete("all")
        self.lbl_grafico.pack_forget()

        if not evolucion:
            lienzo.create_text(
                lienzo.winfo_width() // 2 or 200, 80, text="Sin ventas en el período",
                fill=st.TEXTO_SUAVE, font=(st.FUENTE, 10),
            )
            return

        datos = evolucion
        nota = ""
        if len(datos) > MAX_DIAS_GRAFICO:
            datos = datos[-MAX_DIAS_GRAFICO:]
            nota = (f"Mostrando los últimos {MAX_DIAS_GRAFICO} días con ventas "
                    f"(de {len(evolucion)} en el período).")

        lienzo.update_idletasks()
        ancho = max(lienzo.winfo_width(), 300)
        alto = max(lienzo.winfo_height(), 170)
        borde_inferior = alto - 24
        maximo = max(d["total"] for d in datos) or 1
        hueco = ancho / len(datos)
        ancho_barra = max(6, hueco * 0.62)

        for i, dia in enumerate(datos):
            x0 = i * hueco + (hueco - ancho_barra) / 2
            x1 = x0 + ancho_barra
            altura = max(3, (dia["total"] / maximo) * (borde_inferior - 34))
            y0 = borde_inferior - altura
            lienzo.create_rectangle(x0, y0, x1, borde_inferior,
                                    fill=st.ACENTO, outline="")
            if len(datos) <= 12:
                lienzo.create_text((x0 + x1) / 2, y0 - 8,
                                   text=self._corto(dia["total"]),
                                   fill=st.VERDE_OSCURO,
                                   font=(st.FUENTE, 8, "bold"))
            lienzo.create_text((x0 + x1) / 2, borde_inferior + 12,
                               text=fecha_corta(dia["fecha"])[:5],
                               fill=st.TEXTO_SUAVE, font=(st.FUENTE, 7))

        if nota:
            self.lbl_grafico.config(text=nota)
            self.lbl_grafico.pack(fill="x", pady=(4, 0))

    @staticmethod
    def _corto(valor):
        if valor >= 1000000:
            return f"${valor / 1000000:.1f}M"
        if valor >= 1000:
            return f"${valor / 1000:.0f}k"
        return f"${valor:.0f}"
