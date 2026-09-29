# -*- coding: utf-8 -*-
"""
Pantalla de RENDICIÓN POR BUZÓN.

Dos pestañas:
  1. CARGA / RENDICIÓN  → todos los campos de la planilla (cabecera,
     detalle Tipo/Cantidad/Importe/Total, secciones, cheques y
     observaciones), precargados desde las ventas del día y editables.
  2. CALCULADORA DE BILLETES → conteo de efectivo por denominación.

El total de la calculadora se copia SOLO al campo EFECTIVO de la
pestaña 1 (nunca hay que escribirlo dos veces) y todo lo cargado se
guarda por día con db.guardar_rendicion().
"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

import database as db
import estilos as st
import excel
from util import (money, parse_numero, parse_entero, fecha_a_iso,
                  fecha_corta)

# Secciones de la planilla (todas editables a mano)
SECCIONES = [
    ("gastos", "GASTOS"),
    ("caja", "CAJA"),
    ("envios", "ENVÍOS"),
    ("tarjetas", "TARJETAS"),
    ("transferencias", "TRANSFERENCIAS"),
    ("recibos", "RECIBOS"),
]

PESO_ANCHO = 16


def _num(texto):
    """Importe cargado en un campo ('10.000' / '$10.000' / '10000,50')."""
    n = parse_numero(texto)
    return float(n) if n is not None else 0.0


class RendicionPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._fecha_cargada = None
        self.detalle = []      # [{"tipo", "cantidad", "importe"}]
        self.cheques = []       # [{"cliente", "numero", "banco", "importe"}]
        self.total_billetes = 0.0
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # ---------------- Cabecera (siempre visible, fuera del scroll)
        cab = tk.Frame(self, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(18, 8))

        izq = tk.Frame(cab, bg=st.FONDO)
        izq.pack(side="left")
        tk.Label(izq, text="RENDICIÓN POR BUZÓN", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        tk.Label(izq, text="Carga de datos + calculadora de billetes",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 11)).pack(anchor="w")

        der = tk.Frame(cab, bg=st.FONDO)
        der.pack(side="right")
        self.btn_guardar = tk.Button(
            der, text="GUARDAR RENDICIÓN", command=self._guardar_click,
            relief="flat", bg=st.ACENTO,
            fg="#ffffff", font=(st.FUENTE, 11, "bold"), padx=16, pady=8,
            cursor="hand2")
        self.btn_guardar.pack(anchor="e")
        self.btn_planilla = tk.Button(
            der, text="GENERAR PLANILLA A4", command=self._exportar_click,
            relief="flat", bg=st.VERDE, fg="#ffffff",
            font=(st.FUENTE, 11, "bold"), padx=16, pady=8, cursor="hand2")
        self.btn_planilla.pack(anchor="e", pady=(6, 0))
        self.lbl_estado = tk.Label(der, text="Sin cambios sin guardar",
                                   bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                   font=(st.FUENTE, 9))
        self.lbl_estado.pack(anchor="e", pady=(4, 0))

        # ---------------- Pestañas ----------------
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.tab_carga = tk.Frame(self.notebook, bg=st.FONDO)
        self.tab_billetes = tk.Frame(self.notebook, bg=st.FONDO)
        self.notebook.add(self.tab_carga, text="  1 · CARGA / RENDICIÓN  ")
        self.notebook.add(self.tab_billetes,
                          text="  2 · CALCULADORA DE BILLETES  ")

        contenido = st.contenido_scrollable(self.tab_carga)
        self._lienzo_carga = self.tab_carga.canvas_scroll
        contenido_b = st.contenido_scrollable(self.tab_billetes)
        self._lienzo_billetes = self.tab_billetes.canvas_scroll
        self.canvas_scroll = self._lienzo_carga
        self.notebook.bind("<<NotebookTabChanged>>", self._tab_cambiada)

        self._cargar_cabecera(contenido)
        self._cargar_detalle(contenido)
        self._cargar_secciones(contenido)
        self._cargar_efectivo(contenido)
        self._cargar_cheques(contenido)
        self._cargar_observaciones(contenido)
        self._cargar_calculadora(contenido_b)

    def _tab_cambiada(self, _evento=None):
        # La rueda del mouse hace scroll en la pestaña que se está viendo
        try:
            i = self.notebook.index("current")
        except tk.TclError:
            i = 0
        self.canvas_scroll = (self._lienzo_carga if i == 0
                              else self._lienzo_billetes)

    # ---------------------------------------------------------- pestaña 1
    def _campo(self, padre, label, var, ancho=PESO_ANCHO, fila=None, col=0):
        """Rótulo + entrada en línea dentro de un LabelFrame."""
        celda = tk.Frame(padre, bg=st.FONDO)
        if fila is None:
            celda.pack(side="left", padx=(0, 18))
        else:
            celda.grid(row=fila, column=col, sticky="w", padx=(0, 18),
                       pady=(4, 4))
        tk.Label(celda, text=label, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        e = tk.Entry(celda, textvariable=var, width=ancho,
                     font=(st.FUENTE, 11), bg="#ffffff",
                     highlightbackground=st.BORDE, highlightthickness=1,
                     relief="flat")
        e.pack(anchor="w", ipady=3)
        return e

    def _cargar_cabecera(self, padre):
        marco = st.labelframe(padre, " CABECERA ", padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(16, 0))

        self.var_fecha = tk.StringVar(value=self.app.caja_fecha)
        self.var_chofer = tk.StringVar()
        self.entry_fecha = self._campo(marco, "FECHA (AAA-MM-DD)",
                                       self.var_fecha, ancho=14)
        self._campo(marco, "CHOFER", self.var_chofer, ancho=22)
        self.entry_fecha.bind("<FocusOut>", lambda e: self._recargar_si_cambio())

        acciones = tk.Frame(marco, bg=st.FONDO)
        acciones.pack(side="right", padx=(18, 0))
        tk.Button(acciones, text="Precargar del día", command=self._precargar_click,
                  relief="flat", bg="#e8eef7", fg=st.TEXTO, font=(st.FUENTE, 9),
                  padx=10, pady=4, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(acciones, text="Limpiar todo", command=self._limpiar_click,
                  relief="flat", bg=st.ROJO_CLARO, fg=st.ROJO, font=(st.FUENTE, 9),
                  padx=10, pady=4, cursor="hand2").pack(side="left")

    def _cargar_detalle(self, padre):
        marco = st.labelframe(padre, " DETALLE — TIPO · CANTIDAD · IMPORTE · TOTAL ",
                              padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(14, 0))

        cols = ("tipo", "cantidad", "importe", "total")
        self.tree_detalle = ttk.Treeview(marco, columns=cols, show="headings",
                                         height=6, selectmode="browse")
        for col, txt, ancho, alinea in (("tipo", "TIPO", 320, "w"),
                                        ("cantidad", "CANTIDAD", 110, "e"),
                                        ("importe", "IMPORTE", 150, "e"),
                                        ("total", "TOTAL", 150, "e")):
            self.tree_detalle.heading(col, text=txt, anchor=alinea)
            self.tree_detalle.column(col, width=ancho, anchor=alinea,
                                     stretch=(col == "tipo"))
        self.tree_detalle.pack(fill="x", pady=(0, 8))

        alta = tk.Frame(marco, bg=st.FONDO)
        alta.pack(fill="x")
        self.combo_tipo = ttk.Combobox(alta, width=34, font=(st.FUENTE, 10))
        self.combo_tipo.pack(side="left")
        self.combo_tipo.bind("<<ComboboxSelected>>", self._tipo_elegido)
        self.var_cant_det = tk.StringVar(value="1")
        self.var_imp_det = tk.StringVar()
        for texto, var, ancho in (("Cant.", self.var_cant_det, 7),
                                  ("Importe", self.var_imp_det, 12)):
            tk.Label(alta, text=texto, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 9)).pack(side="left", padx=(10, 4))
            tk.Entry(alta, textvariable=var, width=ancho, font=(st.FUENTE, 11),
                     relief="flat", highlightbackground=st.BORDE,
                     highlightthickness=1).pack(side="left")
        tk.Button(alta, text="+ AGREGAR", command=self._agregar_item,
                  relief="flat", bg=st.ACENTO,
                  fg="#ffffff", font=(st.FUENTE, 10, "bold"), padx=12, pady=4,
                  cursor="hand2").pack(side="left", padx=12)
        tk.Button(alta, text="Quitar fila", command=self._quitar_item,
                  relief="flat", bg="#e8eef7", fg=st.TEXTO, font=(st.FUENTE, 9),
                  padx=10, pady=4, cursor="hand2").pack(side="left")
        tk.Label(alta, text="Enter o + AGREGAR suma la fila",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)
                 ).pack(side="left", padx=12)

        pie = tk.Frame(marco, bg=st.FONDO)
        pie.pack(fill="x", pady=(8, 0))
        tk.Label(pie, text="TOTAL DEL DETALLE", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold")).pack(side="left")
        self.lbl_total_detalle = tk.Label(pie, text=money(0), bg=st.FONDO,
                                          fg=st.VERDE,
                                          font=(st.FUENTE, 13, "bold"))
        self.lbl_total_detalle.pack(side="right")

        # Se pegan las filas con Enter también
        self.combo_tipo.bind("<Return>", lambda e: self._agregar_item())

    def _cargar_secciones(self, padre):
        marco = st.labelframe(padre, " SECCIONES DE LA PLANILLA ", padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(14, 0))
        self.secciones = {}
        for i, (clave, texto) in enumerate(SECCIONES):
            var = tk.StringVar()
            self.secciones[clave] = var
            self._campo(marco, texto, var, fila=i // 3, col=i % 3)
        marco.columnconfigure((0, 1, 2), weight=1)
        tk.Label(marco, text="TARJETAS y TRANSFERENCIAS se precargan con las "
                             "ventas del día; cualquier campo se puede corregir "
                             "a mano.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)
                 ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _cargar_efectivo(self, padre):
        marco = st.labelframe(padre, " EFECTIVO — TOTAL DE BILLETES ", padx=12,
                              pady=8)
        marco.pack(fill="x", padx=24, pady=(14, 0))

        self.var_efectivo = tk.StringVar(value=money(0))
        e = tk.Entry(marco, textvariable=self.var_efectivo, width=18,
                     font=(st.FUENTE, 15, "bold"), state="readonly",
                     readonlybackground=st.VERDE_CLARO, relief="flat",
                     highlightbackground=st.BORDE,
                     highlightthickness=1)
        e.pack(side="left", ipady=4)

        texto = tk.Frame(marco, bg=st.FONDO)
        texto.pack(side="left", padx=(14, 0))
        tk.Label(texto, text="Se completa SOLO: viene de la pestaña "
                             "«2 · CALCULADORA DE BILLETES».",
                 bg=st.FONDO, fg=st.TEXTO, font=(st.FUENTE, 10)
                 ).pack(anchor="w")
        tk.Label(texto, text="Contás los billetes ahí y el importe aparece acá "
                             "y en la planilla A4.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)
                 ).pack(anchor="w")

    def _cargar_cheques(self, padre):
        marco = st.labelframe(padre, " CHEQUES ", padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(14, 0))

        cols = ("cliente", "numero", "banco", "importe")
        self.tree_cheques = ttk.Treeview(marco, columns=cols, show="headings",
                                         height=4, selectmode="browse")
        for col, txt, ancho, alinea in (("cliente", "CLIENTE", 320, "w"),
                                        ("numero", "N.º DE CHEQUE", 160, "w"),
                                        ("banco", "BANCO", 200, "w"),
                                        ("importe", "IMPORTE", 150, "e")):
            self.tree_cheques.heading(col, text=txt, anchor=alinea)
            self.tree_cheques.column(col, width=ancho, anchor=alinea,
                                     stretch=(col == "cliente"))
        self.tree_cheques.pack(fill="x", pady=(0, 8))

        alta = tk.Frame(marco, bg=st.FONDO)
        alta.pack(fill="x")
        self.var_cheque_cliente = tk.StringVar()
        self.var_cheque_numero = tk.StringVar()
        self.var_cheque_banco = tk.StringVar()
        self.var_cheque_importe = tk.StringVar()
        for texto, var, ancho in (("Cliente", self.var_cheque_cliente, 24),
                                  ("N.º cheque", self.var_cheque_numero, 12),
                                  ("Banco", self.var_cheque_banco, 16),
                                  ("Importe", self.var_cheque_importe, 10)):
            tk.Label(alta, text=texto, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 9)).pack(side="left", padx=(0, 4))
            e = tk.Entry(alta, textvariable=var, width=ancho,
                         font=(st.FUENTE, 10), relief="flat",
                         highlightbackground=st.BORDE, highlightthickness=1)
            e.pack(side="left", padx=(0, 10))
            if texto == "Cliente":
                self.entry_cheque_cliente = e
                e.bind("<Return>", lambda _e: self._agregar_cheque())
            if texto == "Importe":
                e.bind("<Return>", lambda _e: self._agregar_cheque())
                var.trace_add("write", lambda *_: self._total_cheques())
        tk.Button(alta, text="+ AGREGAR", command=self._agregar_cheque,
                  relief="flat", bg=st.ACENTO, fg="#ffffff",
                  font=(st.FUENTE, 10, "bold"), padx=12, pady=4,
                  cursor="hand2").pack(side="left", padx=(4, 8))
        tk.Button(alta, text="Quitar", command=self._quitar_cheque,
                  relief="flat", bg="#e8eef7", fg=st.TEXTO, font=(st.FUENTE, 9),
                  padx=10, pady=4, cursor="hand2").pack(side="left")

        pie = tk.Frame(marco, bg=st.FONDO)
        pie.pack(fill="x", pady=(8, 0))
        tk.Label(pie, text="TOTAL CHEQUES", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold")).pack(side="left")
        self.lbl_total_cheques = tk.Label(pie, text=money(0), bg=st.FONDO,
                                          fg=st.TEXTO, font=(st.FUENTE, 13, "bold"))
        self.lbl_total_cheques.pack(side="right")

    def _cargar_observaciones(self, padre):
        marco = st.labelframe(padre, " OBSERVACIONES ", padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(14, 20))
        self.txt_obs = tk.Text(marco, height=3, font=(st.FUENTE, 11),
                               relief="solid", bd=1, bg="#ffffff",
                               highlightthickness=0)
        self.txt_obs.pack(fill="x")

    # ---------------------------------------------------------- pestaña 2
    def _cargar_calculadora(self, padre):
        marco = st.labelframe(padre, " CALCULADORA DE BILLETES — CONTEO DE EFECTIVO ",
                              padx=12, pady=8)
        marco.pack(fill="x", padx=24, pady=(16, 0))

        enc = tk.Frame(marco, bg=st.BARRA, height=30)
        enc.pack(fill="x")
        enc.pack_propagate(False)
        for txt, ancho, lado in (("BILLETE", 160, "left"), ("CANTIDAD", 160, "left"),
                                 ("IMPORTE", 200, "right")):
            tk.Label(enc, text=txt, bg=st.BARRA, fg="#ffffff",
                     font=(st.FUENTE, 10, "bold"), width=ancho // 10,
                     anchor="w" if lado == "left" else "e",
                     padx=10).pack(side=lado)

        self.celdas_billetes = {}
        for denom in db.DENOMINACIONES:
            fila = tk.Frame(marco, bg=st.TARJETA,
                            highlightbackground=st.BORDE, highlightthickness=1)
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text=money(denom), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 13, "bold"), width=16, anchor="w",
                     padx=10).pack(side="left", ipady=4)
            e = tk.Entry(fila, width=10, font=(st.FUENTE, 13), relief="flat",
                         highlightthickness=0, justify="right")
            e.pack(side="left", padx=10, ipady=3)
            e.bind("<KeyRelease>", lambda _e: self._recalcular_billetes())
            self.celdas_billetes[denom] = e
            lbl = tk.Label(fila, text=money(0), bg=st.TARJETA, fg=st.TEXTO,
                           font=(st.FUENTE, 13), width=18, anchor="e",
                           padx=10)
            lbl.pack(side="right", ipady=4)
            setattr(self, f"lbl_billete_{denom}", lbl)

        pie = tk.Frame(marco, bg=st.VERDE_CLARO, highlightbackground=st.BORDE,
                       highlightthickness=1)
        pie.pack(fill="x", pady=(10, 0))
        tk.Label(pie, text="TOTAL EFECTIVO", bg=st.VERDE_CLARO, fg=st.TEXTO,
                 font=(st.FUENTE, 14, "bold"), padx=12, pady=8).pack(side="left")
        self.lbl_total_billetes = tk.Label(pie, text=money(0), bg=st.VERDE_CLARO,
                                           fg=st.TEXTO, font=(st.FUENTE, 20, "bold"),
                                           padx=12, pady=6)
        self.lbl_total_billetes.pack(side="right")

        acciones = tk.Frame(padre, bg=st.FONDO)
        acciones.pack(fill="x", padx=24, pady=(10, 0))
        tk.Button(acciones, text="Limpiar conteo", command=self._limpiar_billetes,
                  relief="flat", bg="#e8eef7", fg=st.TEXTO, font=(st.FUENTE, 10),
                  padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Label(acciones, text="Este total se copia solo al campo EFECTIVO de la "
                                "pestaña 1 y a la planilla A4.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)
                 ).pack(side="left", padx=14)

    # ------------------------------------------------------------ acciones
    def _tipo_elegido(self, _evento=None):
        """Al elegir un producto se completa su precio unitario."""
        nombre = self.combo_tipo.get().strip()
        prod = db.producto_por_nombre(nombre) if nombre else None
        if prod:
            self.var_imp_det.set(money(prod["precio"]))

    def _agregar_item(self):
        tipo = self.combo_tipo.get().strip()
        if not tipo:
            messagebox.showwarning("Detalle",
                                   "Elegí el tipo de producto.", parent=self)
            return
        cant = parse_entero(self.var_cant_det.get())
        if not cant or cant < 1:
            messagebox.showwarning("Detalle",
                                   "La cantidad debe ser 1 o más.", parent=self)
            return
        importe = parse_numero(self.var_imp_det.get())
        if importe is None or importe < 0:
            messagebox.showwarning("Detalle", "Cargá un importe válido.",
                                   parent=self)
            return
        self.detalle.append({"tipo": tipo, "cantidad": int(cant),
                             "importe": float(importe)})
        self._pintar_detalle()
        self.combo_tipo.set("")
        self.var_cant_det.set("1")
        self.var_imp_det.set("")
        self.combo_tipo.focus_set()

    def _quitar_item(self):
        sel = self.tree_detalle.selection()
        if not sel:
            messagebox.showwarning("Detalle", "Elegí la fila a quitar.",
                                   parent=self)
            return
        idx = self.tree_detalle.index(sel[0])
        self.detalle.pop(idx)
        self._pintar_detalle()

    def _pintar_detalle(self):
        self.tree_detalle.delete(*self.tree_detalle.get_children())
        total = 0.0
        for it in self.detalle:
            sub = float(it["cantidad"]) * float(it["importe"])
            total += sub
            self.tree_detalle.insert("", "end", values=(
                it["tipo"], it["cantidad"], money(it["importe"]), money(sub)))
        self.lbl_total_detalle.config(text=money(total))

    def _agregar_cheque(self):
        cliente = self.var_cheque_cliente.get().strip()
        if not cliente:
            messagebox.showwarning("Cheques", "Cargá el cliente.",
                                   parent=self)
            return
        importe = parse_numero(self.var_cheque_importe.get())
        if importe is None or importe <= 0:
            messagebox.showwarning("Cheques", "Cargá un importe válido.",
                                   parent=self)
            return
        self.cheques.append({
            "cliente": cliente,
            "numero": self.var_cheque_numero.get().strip(),
            "banco": self.var_cheque_banco.get().strip(),
            "importe": float(importe),
        })
        self._pintar_cheques()
        self.var_cheque_cliente.set("")
        self.var_cheque_numero.set("")
        self.var_cheque_banco.set("")
        self.var_cheque_importe.set("")
        self.entry_cheque_cliente.focus_set()

    def _quitar_cheque(self):
        sel = self.tree_cheques.selection()
        if not sel:
            messagebox.showwarning("Cheques", "Elegí el cheque a quitar.",
                                   parent=self)
            return
        self.cheques.pop(self.tree_cheques.index(sel[0]))
        self._pintar_cheques()

    def _pintar_cheques(self):
        self.tree_cheques.delete(*self.tree_cheques.get_children())
        for c in self.cheques:
            self.tree_cheques.insert("", "end", values=(
                c["cliente"], c["numero"], c["banco"], money(c["importe"])))
        self.lbl_total_cheques.config(text=money(self._total_cheques()))

    def _total_cheques(self):
        total = sum(float(c["importe"]) for c in self.cheques)
        if hasattr(self, "lbl_total_cheques"):
            self.lbl_total_cheques.config(text=money(total))
        return total

    def _recalcular_billetes(self):
        """Cantidad × valor de cada billete → TOTAL EFECTIVO (y la pestaña 1)."""
        total = 0.0
        for denom in db.DENOMINACIONES:
            e = self.celdas_billetes[denom]
            cant = parse_entero(e.get())
            cant = 0 if cant is None or cant < 0 else cant
            subtotal = denom * cant
            total += subtotal
            getattr(self, f"lbl_billete_{denom}").config(text=money(subtotal))
        self.total_billetes = float(total)
        self.lbl_total_billetes.config(text=money(total))
        self.var_efectivo.set(money(total))
        return self.total_billetes

    def _limpiar_billetes(self):
        for denom in db.DENOMINACIONES:
            self.celdas_billetes[denom].delete(0, "end")
        self._recalcular_billetes()

    # --------------------------------------------------------- guardar/cargar
    def _datos(self):
        return {
            "fecha": self.var_fecha.get().strip(),
            "chofer": self.var_chofer.get().strip(),
            "detalle": [{"tipo": str(i["tipo"]),
                         "cantidad": int(i["cantidad"]),
                         "importe": float(i["importe"])}
                        for i in self.detalle],
            **{clave: _num(var.get()) for clave, var in self.secciones.items()},
            "cheques": [{"cliente": str(c["cliente"]),
                         "numero": str(c["numero"]),
                         "banco": str(c["banco"]),
                         "importe": float(c["importe"])}
                        for c in self.cheques],
            "billetes": {str(d): parse_entero(self.celdas_billetes[d].get()) or 0
                         for d in db.DENOMINACIONES},
            "total_billetes": self._recalcular_billetes(),
            "observaciones": self.txt_obs.get("1.0", "end").strip(),
        }

    def _aplicar(self, datos):
        self.var_fecha.set(datos.get("fecha") or self.app.caja_fecha)
        self.var_chofer.set(datos.get("chofer") or "")
        self.detalle = [{"tipo": str(i.get("tipo", "")),
                         "cantidad": int(i.get("cantidad", 0) or 0),
                         "importe": float(i.get("importe", 0) or 0)}
                        for i in (datos.get("detalle") or [])
                        if i.get("tipo")]
        self._pintar_detalle()
        for clave, var in self.secciones.items():
            valor = datos.get(clave)
            var.set(money(valor) if valor else "")
        self.cheques = [{"cliente": str(c.get("cliente", "")),
                         "numero": str(c.get("numero", "")),
                         "banco": str(c.get("banco", "")),
                         "importe": float(c.get("importe", 0) or 0)}
                        for c in (datos.get("cheques") or [])
                        if c.get("cliente")]
        self._pintar_cheques()
        billetes = datos.get("billetes") or {}
        for denom in db.DENOMINACIONES:
            cant = int(billetes.get(str(denom), 0) or 0)
            e = self.celdas_billetes[denom]
            e.delete(0, "end")
            if cant:
                e.insert(0, str(cant))
        self._recalcular_billetes()
        self.txt_obs.delete("1.0", "end")
        self.txt_obs.insert("1.0", datos.get("observaciones") or "")

    def _vaciar(self):
        """Deja el formulario en cero (sin tocar la base)."""
        self.var_chofer.set("")
        self.detalle = []
        self._pintar_detalle()
        for _clave, var in self.secciones.items():
            var.set("")
        self.cheques = []
        self._pintar_cheques()
        self._limpiar_billetes()
        self.txt_obs.delete("1.0", "end")

    def _guardar(self):
        fecha = fecha_a_iso(self.var_fecha.get())
        if not fecha:
            messagebox.showerror("Rendición",
                                 "La fecha no es válida (usá AAA-MM-DD "
                                 "o DD/MM/AAAA).", parent=self)
            return None
        self.var_fecha.set(fecha)
        datos = self._datos()
        datos["fecha"] = fecha
        db.guardar_rendicion(fecha, datos)
        self._fecha_cargada = fecha
        self.lbl_estado.config(
            text="Guardado " + datetime.now().strftime("%H:%M"))
        return datos

    def _guardar_click(self):
        self._guardar()

    def _exportar_click(self):
        """Guarda lo cargado y arma la planilla A4 lista para imprimir."""
        datos = self._guardar()
        if datos is None:
            return
        fecha = datos.get("fecha") or self.app.caja_fecha
        destino = filedialog.asksaveasfilename(
            parent=self,
            title="Planilla de rendición (una hoja A4)",
            defaultextension=".xlsx",
            initialfile=f"Planilla rendicion {fecha_corta(fecha)}.xlsx",
            filetypes=[("Archivo de Excel", "*.xlsx")],
        )
        if not destino:
            return
        try:
            excel.exportar_rendicion(datos, destino)
        except Exception as exc:
            messagebox.showerror("No se pudo generar la planilla",
                                 f"Ocurrió un error:\n{exc}", parent=self)
            return
        db.log_actividad("Planilla de rendición",
                         f"Rendición del {db.fecha_larga(fecha)} — {destino}")
        messagebox.showinfo(
            "Planilla generada",
            "Se creó la planilla en una sola hoja A4 vertical.\n\n"
            "Para imprimirla: Archivo → Imprimir (o Vista previa de "
            "impresión) y elegir A4 vertical.",
            parent=self)

    def _precargar_click(self):
        if not messagebox.askyesno(
                "Precargar del día",
                "Se completan TARJETAS y TRANSFERENCIAS con las ventas del día "
                "y se limpia lo demás.\n\n¿Continuar?", parent=self):
            return
        self._precargar_del_dia(self.var_fecha.get() or self.app.caja_fecha)

    def _limpiar_click(self):
        if not messagebox.askyesno("Limpiar todo",
                                   "¿Borrar todo lo cargado en la rendición?",
                                   parent=self):
            return
        self._vaciar()
        self.lbl_estado.config(text="Sin cambios sin guardar")

    def _precargar_del_dia(self, fecha):
        """Versión editable de lo que el sistema ya sabe del día."""
        self._vaciar()
        self.var_fecha.set(fecha)
        caja = db.get_caja(fecha)
        if caja:
            r = db.resumen(caja["id"])
            tarjetas = float(r["debito"]) + float(r["credito"])
            if tarjetas:
                self.secciones["tarjetas"].set(money(tarjetas))
            if float(r["transferencias"]):
                self.secciones["transferencias"].set(
                    money(r["transferencias"]))

    def _recargar_si_cambio(self):
        """Si cambiaron la fecha a mano, se trae la rendición de ese día."""
        fecha = fecha_a_iso(self.var_fecha.get())
        if fecha and fecha != self._fecha_cargada:
            self._cargar(fecha)

    def _cargar(self, fecha):
        self._fecha_cargada = fecha
        datos = db.rendicion_de(fecha)
        if datos:
            self._aplicar(datos)
            self.lbl_estado.config(text="Cargada la rendición del día")
        else:
            self._precargar_del_dia(fecha)
            self.lbl_estado.config(text="Sin cambios sin guardar")

    # --------------------------------------------------------------- datos
    def refresh(self):
        """Se llama al entrar a la pantalla y al refrescar el sistema."""
        fecha = getattr(self.app, "caja_fecha", None) or db.hoy()
        if fecha != self._fecha_cargada:
            self._cargar(fecha)
