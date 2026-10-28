# -*- coding: utf-8 -*-
"""Panel de Estadísticas: ventas, medios de pago, evolución y cierres."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta

import database as db
import estilos as st
import excel
import iconos as ic
import ui_comun as uc
from widgets_figma import Tarjeta, Btn
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
        PX = 28
        MUTED = st.TEXTO_SUAVE
        # Contenido con scroll vertical (App._rueda_global usa canvas_scroll)
        cont = st.contenido_scrollable(self)
        self.contenido = cont
        self.canvas = self.canvas_scroll

        # ---------------- Cabecera ----------------
        cab = tk.Frame(cont, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 4))
        tk.Label(cab, text="Estadísticas y reportes", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        self.lbl_periodo = tk.Label(cab, text="", bg=st.FONDO, fg=MUTED,
                                    font=(st.FUENTE, 11))
        self.lbl_periodo.pack(anchor="w", pady=(2, 0))

        # ---------------- Filtros por fecha ----------------
        t, filtros, _h = uc.tarjeta(cont, "Período de consulta", "calendar")
        t.pack(fill="x", padx=PX, pady=(14, 0))
        fila_f = tk.Frame(filtros, bg=st.TARJETA)
        fila_f.pack(fill="x")

        def campo_fecha(texto):
            c = tk.Frame(fila_f, bg=st.TARJETA)
            tk.Label(c, text=texto, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar()
            uc.entrada(c, var, width=12, justify="center").pack(
                pady=(3, 0), ipady=5)
            return var, c

        self.var_desde, f1 = campo_fecha("DESDE (dd/mm/aaaa)")
        self.var_hasta, f2 = campo_fecha("HASTA (dd/mm/aaaa)")
        f1.pack(side="left")
        f2.pack(side="left", padx=(14, 0))

        fila_botones = tk.Frame(fila_f, bg=st.TARJETA)
        fila_botones.pack(side="left", padx=(20, 0), anchor="s", pady=(0, 1))
        self._btn(fila_botones, "Hoy", lambda: self._preset("hoy")).pack(
            side="left", padx=(0, 6))
        self._btn(fila_botones, "Últimos 7 días",
                  lambda: self._preset("semana")).pack(side="left", padx=(0, 6))
        self._btn(fila_botones, "Este mes",
                  lambda: self._preset("mes")).pack(side="left", padx=(0, 6))
        self._btn(fila_botones, "Todo", lambda: self._preset("todo")).pack(
            side="left", padx=(0, 10))
        self._btn(fila_botones, "Actualizar", self._aplicar_fechas,
                  color=st.ACENTO).pack(side="left")

        Btn(fila_f, text="EXPORTAR", command=self._exportar_excel, bg=st.VERDE,
            fg="#ffffff", font=(st.FUENTE, 10, "bold"), padx=20, pady=9
            ).pack(side="right", anchor="s")

        # ---------------- Indicadores ----------------
        marco_cards = tk.Frame(cont, bg=st.FONDO)
        marco_cards.pack(fill="x", padx=PX, pady=(14, 0))
        for c in range(4):
            marco_cards.columnconfigure(c, weight=1, uniform="kpi")

        # (título, clave, columnas que ocupa, icono)
        definiciones = [
            ("Total de ventas", "ventas", 1, "clipboard"),
            ("Garrafas vendidas", "garrafas", 1, "cube"),
            ("Total recaudado", "recaudado", 1, "dollar"),
            ("Ventas promedio", "promedio", 1, "chart"),
            ("Efectivo", "efectivo", 1, "banknote"),
            ("Transferencias", "transferencias", 1, "transfer"),
            ("Tarjetas", "tarjetas", 2, "card"),
            ("Transferencias (cantidad)", "n_transferencias", 1, "transfer"),
            ("Días con ventas", "dias", 1, "calendar"),
            ("Cierres en el período", "cierres", 1, "history"),
            ("Mayor venta del día", "max", 1, "chart"),
        ]
        self.cards = {}
        self.cards_detalle = {}
        fila, col = 0, 0
        for titulo, clave, span, icono in definiciones:
            if col + span > 4:
                fila, col = fila + 1, 0
            destacado = clave == "recaudado"
            t = Tarjeta(marco_cards, radio=12, padx=18, pady=14,
                        borde="#C3D6F8" if destacado else None)
            t.grid(row=fila, column=col, columnspan=span, sticky="nsew",
                   padx=5, pady=5)
            top = tk.Frame(t.cuerpo, bg=st.TARJETA)
            top.pack(fill="x")
            tk.Label(top, text=titulo, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 10)).pack(side="left")
            tk.Label(top, image=ic.cuadro(
                icono, 32, uc.AZUL_I if destacado else uc.GRIS_I,
                uc.AZUL_F if destacado else uc.GRIS_F, 8, 17),
                bg=st.TARJETA).pack(side="right")
            lbl = tk.Label(t.cuerpo, text="—", bg=st.TARJETA, fg=st.TEXTO,
                           font=(st.FUENTE, 22), anchor="w")
            lbl.pack(anchor="w", pady=(8, 0))
            det = tk.Label(t.cuerpo, text="", bg=st.TARJETA, fg=MUTED,
                           font=(st.FUENTE, 9), anchor="w")
            det.pack(anchor="w")
            self.cards[clave] = lbl
            self.cards_detalle[clave] = det
            col += span
        self.cards["recaudado"].config(fg=st.VERDE_OSCURO)

        # ---------------- Producto + evolución ----------------
        medio = tk.Frame(cont, bg=st.FONDO)
        medio.pack(fill="x", padx=PX, pady=(9, 0))
        medio.columnconfigure(0, weight=1, uniform="med")
        medio.columnconfigure(1, weight=1, uniform="med")
        medio.rowconfigure(0, weight=1)

        t_izq, izq, _h = uc.tarjeta(medio, "Ventas por producto", "cube")
        t_izq.grid(row=0, column=0, sticky="nsew", padx=(5, 5))
        marco_prod = tk.Frame(izq, bg=st.TARJETA)
        marco_prod.pack(fill="both", expand=True)
        scroll_prod = ttk.Scrollbar(marco_prod, orient="vertical")
        scroll_prod.pack(side="right", fill="y")
        self.tree_productos = ttk.Treeview(
            marco_prod, columns=("producto", "garrafas", "total"),
            show="headings", height=6, yscrollcommand=scroll_prod.set)
        self.tree_productos.heading("producto", text="Producto")
        self.tree_productos.heading("garrafas", text="Garrafas")
        self.tree_productos.heading("total", text="Total")
        self.tree_productos.column("producto", width=180, anchor="w")
        self.tree_productos.column("garrafas", width=90, anchor="center")
        self.tree_productos.column("total", width=130, anchor="e")
        self.tree_productos.pack(side="left", fill="both", expand=True)
        scroll_prod.config(command=self.tree_productos.yview)

        t_der, der, _h = uc.tarjeta(medio, "Evolución de ventas por día", "chart")
        t_der.grid(row=0, column=1, sticky="nsew", padx=(5, 5))
        self.canvas_grafico = tk.Canvas(der, bg=st.TARJETA, highlightthickness=0,
                                        height=230)
        self.canvas_grafico.pack(fill="both", expand=True)
        self.lbl_grafico = tk.Label(der, text="", bg=st.TARJETA, fg=MUTED,
                                    font=(st.FUENTE, 9), anchor="w")
        self._evolucion = None
        self._tam_grafico = (0, 0)
        self.canvas_grafico.bind("<Configure>", self._al_redimensionar_grafico)

        # ---------------- Cierres ----------------
        t_c, cierres_frame, _h = uc.tarjeta(cont, "Resumen de cierres de caja",
                                            "history")
        t_c.pack(fill="x", padx=PX, pady=(14, 24))

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

    def _btn(self, parent, texto, comando, color="#E8EEF7"):
        gris = color == "#E8EEF7"
        return Btn(parent, text=texto, command=comando, bg=color,
                   fg=st.TEXTO if gris else "#ffffff",
                   font=(st.FUENTE, 9, "bold"), padx=14, pady=8)

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
                     "#B45309" if etiqueta == "sobrante" else st.VERDE_OSCURO)
            self.tree_cierres.tag_configure(etiqueta, foreground=color)
            self.tree_cierres.item(self.tree_cierres.get_children()[-1],
                                   tags=(etiqueta,))

    def _dibujar_grafico(self, evolucion):
        """Guarda los datos y dibuja el gráfico (se redibuja al cambiar de tamaño)."""
        self._evolucion = evolucion
        self._pintar_grafico()

    def _al_redimensionar_grafico(self, evento):
        if (evento.width, evento.height) == self._tam_grafico:
            return
        self._tam_grafico = (evento.width, evento.height)
        self._pintar_grafico()

    def _pintar_grafico(self):
        lienzo = self.canvas_grafico
        evolucion = self._evolucion
        lienzo.delete("all")
        self.lbl_grafico.pack_forget()
        ancho = max(lienzo.winfo_width(), 300)
        alto = max(lienzo.winfo_height(), 200)

        if not evolucion:
            lienzo.create_text(ancho // 2, alto // 2,
                               text="Sin ventas en el período",
                               fill=st.TEXTO_SUAVE, font=(st.FUENTE, 10))
            return

        datos = evolucion
        nota = ""
        if len(datos) > MAX_DIAS_GRAFICO:
            datos = datos[-MAX_DIAS_GRAFICO:]
            nota = (f"Mostrando los últimos {MAX_DIAS_GRAFICO} días con ventas "
                    f"(de {len(evolucion)} en el período).")

        izq, der, arriba, abajo = 54, 12, 18, 28
        base = alto - abajo
        area = base - arriba
        maximo = max(d["total"] for d in datos) or 1

        # Líneas guía con su valor
        for frac in (0, 0.5, 1):
            y = base - area * frac
            lienzo.create_line(izq, y, ancho - der, y,
                               fill="#E3E9F3" if frac else "#CBD5E1")
            lienzo.create_text(izq - 8, y, anchor="e",
                               text=self._corto(maximo * frac) if frac else "$0",
                               fill=st.TEXTO_SUAVE, font=(st.FUENTE, 8))

        hueco = (ancho - izq - der) / len(datos)
        ancho_barra = max(6, min(46, hueco * 0.62))
        paso = max(1, int(38 / hueco) + 1) if hueco < 38 else 1

        for i, dia in enumerate(datos):
            x0 = izq + i * hueco + (hueco - ancho_barra) / 2
            x1 = x0 + ancho_barra
            altura = max(3, (dia["total"] / maximo) * area)
            y0 = base - altura
            es_max = dia["total"] == maximo
            lienzo.create_rectangle(x0, y0, x1, base, outline="",
                                    fill=st.ACENTO_OSCURO if es_max else st.ACENTO)
            if len(datos) <= 12:
                lienzo.create_text((x0 + x1) / 2, y0 - 9,
                                   text=self._corto(dia["total"]),
                                   fill=st.VERDE_OSCURO,
                                   font=(st.FUENTE, 8, "bold"))
            if i % paso == 0:
                lienzo.create_text((x0 + x1) / 2, base + 14,
                                   text=fecha_corta(dia["fecha"])[:5],
                                   fill=st.TEXTO_SUAVE, font=(st.FUENTE, 8))

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
