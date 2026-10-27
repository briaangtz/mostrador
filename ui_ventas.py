# -*- coding: utf-8 -*-
"""Panel de registro de ventas.

Una venta es un TICKET: primero se arman los productos (uno o varios) y
después se reparte el pago entre uno o varios medios de pago, siempre que
la suma de los importes dé exactamente el total de la venta.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import estilos as st
import iconos as ic
from widgets_figma import Tarjeta, Btn, Aviso
from util import money, parse_entero, parse_numero, fecha_larga


class VentasPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._productos = []
        self._items = []            # productos ya agregados al ticket
        self._pagos = []            # medios de pago ya agregados
        self._linea_tocada = False  # el usuario cambió la fila de producto
        self._cargando = False      # evita marcar "tocado" al autocompletar
        self._pagos_fijos = False   # el único pago sigue al total del ticket
        self._total = 0.0
        self._editando_id = None
        self._construir()

    def _construir(self):
        PX = 28                                    # margen lateral (igual que Inicio)
        MUTED = st.TEXTO_SUAVE
        contenido = st.contenido_scrollable(self)

        # ---------------- Cabecera ----------------
        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 6))
        self._cab = cab
        tk.Label(cab, text="Registro de ventas", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        self.lbl_sub = tk.Label(cab, text="", bg=st.FONDO, fg=MUTED,
                                font=(st.FUENTE, 11), justify="left", anchor="w")
        self.lbl_sub.pack(anchor="w", pady=(2, 0))

        # Aviso de caja cerrada / sin abrir (se muestra desde refresh)
        self.lbl_bloqueada = Aviso(contenido)

        # ---------------- Utilidades de armado ----------------
        def tarjeta(parent, titulo, icono, **pack):
            t = Tarjeta(parent, radio=12, padx=20, pady=16)
            t.pack(**pack)
            h = tk.Frame(t.cuerpo, bg=st.TARJETA)
            h.pack(fill="x", pady=(0, 12))
            tk.Label(h, image=ic.icono(icono, 20, "#64748B"),
                     bg=st.TARJETA).pack(side="left", padx=(0, 10))
            tk.Label(h, text=titulo, bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 12, "bold")).pack(side="left")
            return t, t.cuerpo

        def entrada(parent, var):
            e = tk.Entry(parent, textvariable=var, font=(st.FUENTE, 11),
                         relief="flat", bd=0, bg="#FFFFFF", fg=st.TEXTO,
                         insertbackground=st.TEXTO, highlightthickness=1,
                         highlightbackground="#D9E0EC",
                         highlightcolor=st.ACENTO,
                         disabledbackground="#F1F5F9",
                         disabledforeground=MUTED)
            e.pack(fill="x", pady=(4, 0), ipady=7)
            return e

        def seccion_lista(parent, titulo):
            t = Tarjeta(parent, fondo="#F8FAFC", radio=10, padx=12, pady=10,
                        exterior=st.TARJETA)
            tk.Label(t.cuerpo, text=titulo, bg="#F8FAFC", fg=MUTED,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w", pady=(0, 6))
            return t, t.cuerpo

        # ---------------- Formulario ----------------
        form_card, form = tarjeta(contenido, "Nueva venta", "cart",
                                  fill="x", padx=PX, pady=(12, 0))

        # Cómo se usa, en dos pasos: se ve siempre, sin scrollear
        pasos = tk.Frame(form, bg=st.TARJETA)
        pasos.pack(fill="x", pady=(0, 12))
        for n, txt in (
                (1, "Producto, cantidad y precio → botón + AGREGAR AL TICKET "
                    "(uno por cada producto del ticket)."),
                (2, "Medio de pago → botón REGISTRAR VENTA "
                    "(el importe se carga solo con lo que falta).")):
            f = tk.Frame(pasos, bg=st.TARJETA)
            f.pack(anchor="w", pady=2)
            tk.Label(f, image=ic.avatar(str(n), 20, st.ACENTO, "#FFFFFF", 0.62),
                     bg=st.TARJETA).pack(side="left", padx=(0, 8))
            tk.Label(f, text=txt, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 10)).pack(side="left")
        self.lbl_pasos = pasos

        # Dos filas de 4 campos: en pantallas chicas nada queda cortado
        grid = tk.Frame(form, bg=st.TARJETA)
        grid.pack(fill="x")
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="campo")

        def campo(col, etiqueta, fila=0):
            celda = tk.Frame(grid, bg=st.TARJETA)
            celda.grid(row=fila, column=col, sticky="nsew",
                       padx=(0 if col == 0 else 8, 0 if col == 3 else 8),
                       pady=(0, 10))
            lbl = tk.Label(celda, text=etiqueta, bg=st.TARJETA, fg=MUTED,
                           font=(st.FUENTE, 9, "bold"), anchor="w",
                           justify="left")
            lbl.pack(fill="x")
            celda.bind("<Configure>", lambda e, l=lbl: l.configure(
                wraplength=max(60, e.width - 2)))
            return celda, lbl

        # Fila 1: qué se lleva el cliente
        c_producto, _ = campo(0, "PRODUCTO", 0)
        self.combo_producto = ttk.Combobox(c_producto, state="readonly",
                                           width=22, font=(st.FUENTE, 11))
        self.combo_producto.pack(fill="x", pady=(4, 0))
        self.combo_producto.bind("<<ComboboxSelected>>", self._producto_cambiado)

        c_cantidad, _ = campo(1, "CANTIDAD", 0)
        self.var_cantidad = tk.StringVar(value="1")
        self.spin_cantidad = ttk.Spinbox(c_cantidad, from_=1, to=9999, width=8,
                                         textvariable=self.var_cantidad,
                                         font=(st.FUENTE, 11), justify="center",
                                         command=self._linea_modificada)
        self.spin_cantidad.pack(fill="x", pady=(4, 0))
        self.var_cantidad.trace_add("write", self._linea_modificada)

        c_precio, _ = campo(2, "PRECIO UNITARIO", 0)
        self.var_precio = tk.StringVar(value="")
        self.ent_precio = entrada(c_precio, self.var_precio)
        self.var_precio.trace_add("write", self._linea_modificada)

        # Nombre de la persona / cliente (aparece en el Excel exportado)
        c_cliente, _ = campo(3, "NOMBRE / CLIENTE (opcional)", 0)
        self.var_cliente = tk.StringVar(value="")
        self.ent_cliente = entrada(c_cliente, self.var_cliente)

        # Fila 2: cómo paga (uno o varios medios, cada uno con su importe)
        c_medio, _ = campo(0, "MEDIO DE PAGO", 1)
        self.combo_medio = ttk.Combobox(c_medio, state="readonly", width=18,
                                        values=db.MEDIOS_PAGO,
                                        font=(st.FUENTE, 11))
        self.combo_medio.set(db.MEDIOS_PAGO[0])
        self.combo_medio.pack(fill="x", pady=(4, 0))
        self.combo_medio.bind("<<ComboboxSelected>>", self._medio_cambiado)

        c_importe, self.lbl_importe = campo(1, "IMPORTE", 1)
        self.lbl_importe.config(wraplength=235, justify="left")
        self.var_importe = tk.StringVar(value="")
        self.ent_importe = entrada(c_importe, self.var_importe)
        self.var_importe.trace_add("write", self._importe_modificado)

        # N° de comprobante: obligatorio para Transferencia
        c_comprobante, self.lbl_comprobante = campo(2, "N° DE COMPROBANTE", 1)
        self.var_comprobante = tk.StringVar(value="")
        self.ent_comprobante = entrada(c_comprobante, self.var_comprobante)

        # CÓDIGO DE MUTUAL: obligatorio para BONO (mínimo 3 números).
        # Ocupa el mismo lugar que el comprobante; se muestra uno u otro.
        c_mutual, self.lbl_mutual = campo(2, "CÓDIGO DE MUTUAL", 1)
        self.var_mutual = tk.StringVar(value="")
        self.ent_mutual = entrada(c_mutual, self.var_mutual)
        self._c_comprobante = c_comprobante
        self._c_mutual = c_mutual
        c_mutual.grid_remove()

        c_total, _ = campo(3, "TOTAL DEL TICKET", 1)
        caja_total = Tarjeta(c_total, fondo="#ECF7F0", borde="#BDE5CD",
                             radio=10, padx=12, pady=7, exterior=st.TARJETA)
        caja_total.pack(fill="x", pady=(4, 0))
        self.lbl_total = tk.Label(caja_total.cuerpo, text="$0", bg="#ECF7F0",
                                  fg=st.VERDE_OSCURO,
                                  font=(st.FUENTE, 16, "bold"), anchor="e")
        self.lbl_total.pack(fill="x")

        # Qué tiene adentro el total + cuadre: se ve arriba de todo, sin bajar
        self.lbl_desglose = tk.Label(form, text="", bg=st.TARJETA, fg=MUTED,
                                     font=(st.FUENTE, 10), justify="right",
                                     anchor="e", wraplength=880)
        self.lbl_desglose.pack(anchor="e", pady=(2, 0))

        caja_pago = Tarjeta(form, fondo="#F8FAFC", borde=st.BORDE, radio=10,
                            padx=14, pady=7, exterior=st.TARJETA)
        caja_pago.pack(anchor="e", pady=(6, 0))
        self.lbl_pago = tk.Label(caja_pago.cuerpo, text="", bg="#F8FAFC",
                                 fg=MUTED, font=(st.FUENTE, 11, "bold"),
                                 justify="right", anchor="e", wraplength=760)
        self.lbl_pago.pack()

        # ---------------- Acciones del ticket ----------------
        acciones = tk.Frame(form, bg=st.TARJETA)
        acciones.pack(fill="x", pady=(14, 0))

        self.btn_agregar_item = Btn(
            acciones, text="+ AGREGAR AL TICKET", command=self._agregar_item,
            bg=st.ACENTO, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=9)
        self.btn_agregar_item.pack(side="left")

        self.btn_agregar_pago = Btn(
            acciones, text="+ AGREGAR MEDIO DE PAGO", command=self._agregar_pago,
            bg=st.BARRA, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=9)
        self.btn_agregar_pago.pack(side="left", padx=(10, 0))

        self.btn_registrar = Btn(
            acciones, text="REGISTRAR VENTA", command=self._registrar,
            bg=st.VERDE, fg="#ffffff", font=(st.FUENTE, 11, "bold"),
            padx=24, pady=10)
        self.btn_registrar.pack(side="right")

        # ---------------- Listas del ticket ----------------
        listas = tk.Frame(form, bg=st.TARJETA)
        listas.pack(fill="both", expand=True, pady=(14, 0))
        listas.columnconfigure(0, weight=3, uniform="lst")
        listas.columnconfigure(1, weight=2, uniform="lst")
        listas.rowconfigure(0, weight=1)

        t_items, marco_items = seccion_lista(listas, "PRODUCTOS DEL TICKET")
        t_items.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        zona_i = tk.Frame(marco_items, bg="#F8FAFC")
        zona_i.pack(fill="both", expand=True)
        self.tree_items = ttk.Treeview(
            zona_i, columns=("producto", "cantidad", "precio", "subtotal"),
            show="headings", height=3)
        self.tree_items.heading("producto", text="Producto")
        self.tree_items.heading("cantidad", text="Cantidad")
        self.tree_items.heading("precio", text="Precio unitario")
        self.tree_items.heading("subtotal", text="Subtotal")
        self.tree_items.column("producto", width=170, anchor="w")
        self.tree_items.column("cantidad", width=65, anchor="center")
        self.tree_items.column("precio", width=100, anchor="e")
        self.tree_items.column("subtotal", width=95, anchor="e")
        scroll_i = ttk.Scrollbar(zona_i, orient="vertical",
                                 command=self.tree_items.yview)
        self.tree_items.configure(yscrollcommand=scroll_i.set)
        scroll_i.pack(side="right", fill="y")
        self.tree_items.pack(fill="both", expand=True)

        pie_items = tk.Frame(marco_items, bg="#F8FAFC")
        pie_items.pack(fill="x", pady=(8, 0))
        self.btn_quitar_item = Btn(
            pie_items, text="Quitar seleccionado", command=self._quitar_item,
            bg="#E5EAF1", fg=st.TEXTO, font=(st.FUENTE, 9), padx=12, pady=5)
        self.btn_quitar_item.pack(side="left")

        t_pagos, marco_pagos = seccion_lista(listas, "FORMAS DE PAGO")
        t_pagos.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        zona_p = tk.Frame(marco_pagos, bg="#F8FAFC")
        zona_p.pack(fill="both", expand=True)
        self.tree_pagos = ttk.Treeview(
            zona_p, columns=("medio", "importe", "comprobante"),
            show="headings", height=3)
        self.tree_pagos.heading("medio", text="Medio")
        self.tree_pagos.heading("importe", text="Importe")
        self.tree_pagos.heading("comprobante", text="Comprobante")
        self.tree_pagos.column("medio", width=135, anchor="w")
        self.tree_pagos.column("importe", width=95, anchor="e")
        self.tree_pagos.column("comprobante", width=115, anchor="w")
        scroll_p = ttk.Scrollbar(zona_p, orient="vertical",
                                 command=self.tree_pagos.yview)
        self.tree_pagos.configure(yscrollcommand=scroll_p.set)
        scroll_p.pack(side="right", fill="y")
        self.tree_pagos.pack(fill="both", expand=True)
        self.tree_pagos.bind("<<TreeviewSelect>>", self._pago_seleccionado)

        pie_pagos = tk.Frame(marco_pagos, bg="#F8FAFC")
        pie_pagos.pack(fill="x", pady=(8, 0))
        self.btn_quitar_pago = Btn(
            pie_pagos, text="Quitar seleccionado", command=self._quitar_pago,
            bg="#E5EAF1", fg=st.TEXTO, font=(st.FUENTE, 9), padx=12, pady=5)
        self.btn_quitar_pago.pack(side="left")

        # Estado del cuadre / mensajes de edición
        self.lbl_info = tk.Label(form, text="", bg=st.TARJETA, fg=st.TEXTO,
                                 font=(st.FUENTE, 11, "bold"), anchor="w")
        self.lbl_info.pack(fill="x", pady=(10, 0))

        # ---------------- Listado de ventas ----------------
        lista_card, marco_lista = tarjeta(contenido, "Ventas registradas",
                                          "clipboard", fill="both",
                                          expand=True, padx=PX, pady=(14, 0))

        zona = tk.Frame(marco_lista, bg=st.TARJETA)
        zona.pack(fill="both", expand=True)
        columnas = ("ticket", "hora", "productos", "cantidad", "cliente",
                    "medios", "comprobante", "total", "cajero")
        self.tree = ttk.Treeview(zona, columns=columnas, show="headings",
                                 height=10, selectmode="extended")
        self.tree.heading("ticket", text="#")
        self.tree.heading("hora", text="Hora")
        self.tree.heading("productos", text="Productos del ticket")
        self.tree.heading("cantidad", text="Cant.")
        self.tree.heading("cliente", text="Nombre / Cliente")
        self.tree.heading("medios", text="Formas de pago")
        self.tree.heading("comprobante", text="N° Comprobante")
        self.tree.heading("total", text="Total")
        self.tree.heading("cajero", text="Registró")

        self.tree.column("ticket", width=46, anchor="center", stretch=False)
        self.tree.column("hora", width=56, anchor="center", stretch=False)
        self.tree.column("productos", width=200, anchor="w")
        self.tree.column("cantidad", width=54, anchor="center", stretch=False)
        self.tree.column("cliente", width=100, anchor="w")
        self.tree.column("medios", width=165, anchor="w")
        self.tree.column("comprobante", width=110, anchor="w")
        self.tree.column("total", width=95, anchor="e")
        self.tree.column("cajero", width=80, anchor="w")

        scroll = ttk.Scrollbar(zona, orient="vertical", command=self.tree.yview)
        scroll_h = ttk.Scrollbar(zona, orient="horizontal",
                                 command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set,
                            xscrollcommand=scroll_h.set)
        # Las barras se ubican primero: el listado ocupa el resto
        scroll.pack(side="right", fill="y")
        scroll_h.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        pie = tk.Frame(marco_lista, bg=st.TARJETA)
        pie.pack(fill="x", pady=(12, 0))

        self.btn_editar = Btn(
            pie, text="Editar venta seleccionada", command=self._editar,
            bg=st.ACENTO, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=8)
        self.btn_editar.pack(side="left")

        self.btn_eliminar = Btn(
            pie, text="Eliminar seleccionadas", command=self._eliminar,
            bg=st.ROJO, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=8)
        self.btn_eliminar.pack(side="left", padx=(10, 0))

        self.btn_vaciar = Btn(
            pie, text="Borrar toda la caja", command=self._vaciar_caja,
            bg="#7f1d1d", fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=8)
        self.btn_vaciar.pack(side="left", padx=(10, 0))

        self.btn_cancelar = Btn(
            pie, text="Cancelar edición", command=self._cancelar_edicion,
            bg="#E5EAF1", fg=st.TEXTO, font=(st.FUENTE, 10), padx=16, pady=8)

        self.lbl_pie = tk.Label(pie, text="", bg=st.TARJETA, fg=MUTED,
                                font=(st.FUENTE, 10), wraplength=420,
                                justify="right", anchor="e")
        self.lbl_pie.pack(side="right")

        # ---------------- Ayuda ----------------
        ayuda = tk.Frame(contenido, bg=st.FONDO)
        ayuda.pack(fill="x", padx=PX, pady=(12, 24))
        tk.Label(ayuda, image=ic.icono("info", 16, "#94A3B8", 1.9),
                 bg=st.FONDO).pack(side="left", anchor="n", padx=(0, 8), pady=1)
        self.lbl_ayuda = tk.Label(
            ayuda,
            text="Armá el ticket: cargá el producto y presioná "
                 "+ AGREGAR AL TICKET (repetí por cada producto). Después "
                 "cargá el medio de pago y su importe con "
                 "+ AGREGAR MEDIO DE PAGO (si hay más de uno, que sumen el "
                 "total) y registrá. ¿Cargaste de más? Seleccioná una o varias "
                 "ventas (Ctrl o Shift + clic) y usá Editar, Eliminar "
                 "seleccionadas o Borrar toda la caja.",
            bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 9), wraplength=760,
            anchor="w", justify="left")
        self.lbl_ayuda.pack(side="left", fill="x", expand=True)
        ayuda.bind("<Configure>", lambda e: self.lbl_ayuda.configure(
            wraplength=max(200, e.width - 40)))

        self._pintar_items()
        self._pintar_pagos()

    # ------------------------------------------------------------- acciones
    def _sin_permiso_ventas(self):
        """True (y avisa) si la sesión no puede operar ventas."""
        if db.puede("ventas"):
            return False
        messagebox.showerror("Sin permisos",
                             "Tu usuario no tiene permiso para operar ventas.",
                             parent=self)
        return True

    def _producto_cambiado(self, _=None):
        idx = self.combo_producto.current()
        if 0 <= idx < len(self._productos):
            p = self._productos[idx]
            if not self._cargando:
                self._linea_tocada = True
            self.var_precio.set(money(p["precio"]).replace("$", ""))
            self._recalcular()

    def _medio_cambiado(self, _=None):
        """Actualiza el aviso del N° de comprobante y campos BONO según el medio."""
        medio = self.combo_medio.get()
        es_transferencia = medio == "Transferencia"
        es_bono = medio == "BONO"

        # N° de comprobante
        if es_transferencia:
            self.lbl_comprobante.config(
                text="N° DE COMPROBANTE (OBLIGATORIO)", fg=st.ROJO,
                font=(st.FUENTE, 9, "bold"),
            )
            self.ent_comprobante.config(bg="#fff7f7")
        else:
            self.lbl_comprobante.config(
                text="N° DE COMPROBANTE (opcional)", fg=st.TEXTO_SUAVE,
                font=(st.FUENTE, 9, "bold"),
            )
            self.ent_comprobante.config(bg="#ffffff")

        # Se muestra el campo que corresponde al medio de pago
        if es_bono:
            self._c_comprobante.grid_remove()
            self._c_mutual.grid()
        else:
            self._c_mutual.grid_remove()
            self._c_comprobante.grid()

        # CÓDIGO DE MUTUAL (BONO)
        if es_bono:
            self.lbl_mutual.config(
                text="CÓDIGO DE MUTUAL (OBLIGATORIO, mín. 3 números)", fg=st.ROJO,
                font=(st.FUENTE, 9, "bold"),
            )
            self.ent_mutual.config(bg="#fff7f7")
        else:
            self.lbl_mutual.config(
                text="CÓDIGO DE MUTUAL (opcional)", fg=st.TEXTO_SUAVE,
                font=(st.FUENTE, 9, "bold"),
            )
            self.ent_mutual.config(bg="#ffffff")

    def _linea_modificada(self, *_):
        """El usuario tocó la fila de producto: entra al ticket al registrar."""
        if not self._cargando:
            self._linea_tocada = True
        self._recalcular()

    def _importe_modificado(self, *_):
        """Si cargó un importe a mano, ese medio deja de seguir al total."""
        if not self._cargando and self.var_importe.get().strip():
            self._pagos_fijos = False
        self._recalcular()

    def _medios_permitidos(self):
        """Medios de pago que el usuario puede registrar."""
        return [m for m in db.MEDIOS_PAGO if db.puede(db.MEDIO_PERMISO[m])]

    # ------------------------------------------------- ticket: productos
    def _datos_linea(self, avisos=True):
        """(producto, cantidad, precio) de la fila cargada, o None."""
        idx = self.combo_producto.current()
        if idx < 0 or idx >= len(self._productos):
            if avisos:
                messagebox.showwarning("Venta", "Seleccioná un producto.",
                                       parent=self)
            return None
        producto = self._productos[idx]
        cantidad = parse_entero(self.var_cantidad.get())
        precio = parse_numero(self.var_precio.get())
        if not producto:
            if avisos:
                messagebox.showwarning("Venta", "Seleccioná un producto.",
                                       parent=self)
            return None
        if not cantidad or cantidad <= 0:
            if avisos:
                messagebox.showwarning("Venta", "Ingresá una cantidad válida.",
                                       parent=self)
            return None
        if precio is None or precio <= 0:
            if avisos:
                messagebox.showwarning("Venta",
                                       "Ingresá un precio unitario válido.",
                                       parent=self)
            return None
        return producto, cantidad, precio

    def _total_linea(self):
        cantidad = parse_entero(self.var_cantidad.get()) or 0
        precio = parse_numero(self.var_precio.get()) or 0
        return cantidad * precio

    def _total_ticket(self):
        """Total del ticket: lo agregado + la fila cargada si corresponde."""
        total = sum(i["cantidad"] * i["precio_unitario"] for i in self._items)
        if not self._items or self._linea_tocada:
            total += self._total_linea()
        return total

    def _pintar_items(self):
        self.tree_items.delete(*self.tree_items.get_children())
        for i, it in enumerate(self._items):
            self.tree_items.insert("", "end", iid=str(i), values=(
                it.get("producto") or "—",
                it["cantidad"],
                money(it["precio_unitario"]),
                money(it["cantidad"] * it["precio_unitario"]),
            ))

    def _agregar_item(self):
        if self._sin_permiso_ventas():
            return
        datos = self._datos_linea()
        if not datos:
            return
        producto, cantidad, precio = datos
        for it in self._items:
            # Mismo producto al mismo precio: se suman las unidades
            if (it["producto_id"] == producto["id"]
                    and abs(it["precio_unitario"] - precio) < 0.01):
                it["cantidad"] += cantidad
                break
        else:
            self._items.append({
                "producto_id": producto["id"],
                "cantidad": cantidad,
                "precio_unitario": precio,
                "producto": producto["nombre"],
            })
        self._cargando = True
        try:
            self.var_cantidad.set("1")
        finally:
            self._cargando = False
        self._linea_tocada = False
        self._pintar_items()
        self._recalcular()

    def _quitar_item(self):
        sel = self.tree_items.selection()
        if not sel:
            messagebox.showwarning("Ticket",
                                   "Elegí un producto de la lista para "
                                   "quitarlo del ticket.", parent=self)
            return
        for iid in sorted((int(i) for i in sel), reverse=True):
            if 0 <= iid < len(self._items):
                del self._items[iid]
        self._pintar_items()
        self._recalcular()

    # --------------------------------------------------- ticket: pagos
    def _pago_aplica(self):
        """True si la fila de medio de pago todavía hay que tener en cuenta."""
        if not self._pagos:
            return True
        # Ya hay medios cargados: la fila solo sirve si se cargó un importe
        return bool(self.var_importe.get().strip())

    def _pago_pendiente(self, total, avisos=False, forzar=False):
        """Pago de la fila todavía no agregado (o None si no aplica)."""
        if not forzar and not self._pago_aplica():
            return None
        medio = self.combo_medio.get()
        comprobante = self.var_comprobante.get().strip() or None
        if medio not in db.MEDIOS_PAGO:
            if avisos:
                messagebox.showwarning("Venta", "Seleccioná el medio de pago.",
                                       parent=self)
            return None
        permiso_medio = db.MEDIO_PERMISO.get(medio)
        if permiso_medio and not db.puede(permiso_medio):
            if avisos:
                messagebox.showerror(
                    "Sin permisos",
                    "Tu usuario no tiene permiso para registrar cobros con "
                    f"{medio}.",
                    parent=self,
                )
            return None
        txt = self.var_importe.get().strip()
        if txt:
            importe = parse_numero(txt)
            if importe is None or importe <= 0:
                if avisos:
                    messagebox.showwarning(
                        "Importe",
                        f"Ingresá un importe válido para {medio}.",
                        parent=self,
                    )
                return None
        else:
            importe = total - sum(p["importe"] for p in self._pagos)
            if importe <= 0:
                if avisos:
                    messagebox.showwarning(
                        "Ticket completo",
                        "Los medios de pago ya cubren el total. Si querés "
                        "cargar otro, quitalo o ingresá un importe.",
                        parent=self,
                    )
                return None
        if medio == "Transferencia" and not comprobante:
            if avisos:
                messagebox.showerror(
                    "Falta el comprobante",
                    "Para registrar una venta paga con TRANSFERENCIA es "
                    "obligatorio ingresar el N° de comprobante.\n\n"
                    "Ingresá el número y volvé a presionar el botón.",
                    parent=self,
                )
                self.ent_comprobante.focus_set()
            return None
        if medio == "BONO":
            mutual = self.var_mutual.get().strip()
            if not mutual:
                if avisos:
                    messagebox.showerror(
                        "Falta el código de mutual",
                        "Para registrar una venta paga con BONO es "
                        "obligatorio ingresar el CÓDIGO DE MUTUAL.\n\n"
                        "Ingresá el código y volvé a presionar el botón.",
                        parent=self,
                    )
                    self.ent_mutual.focus_set()
                return None
            # Validar mínimo 3 números
            digitos = "".join(ch for ch in mutual if ch.isdigit())
            if len(digitos) < 3:
                if avisos:
                    messagebox.showerror(
                        "Código de mutual inválido",
                        "El CÓDIGO DE MUTUAL debe contener al menos 3 números.\n\n"
                        f"Tenés: {len(digitos)} número(s). Ingresá al menos 3.",
                        parent=self,
                    )
                    self.ent_mutual.focus_set()
                return None
            return {"medio": medio, "importe": float(importe),
                    "comprobante": comprobante,
                    "mutual": mutual}
        return {"medio": medio, "importe": float(importe),
                "comprobante": comprobante}

    def _pintar_pagos(self):
        self.tree_pagos.delete(*self.tree_pagos.get_children())
        for i, p in enumerate(self._pagos):
            medio = p["medio"]
            comprobante = p.get("comprobante") or "—"
            if medio == "BONO":
                comprobante = f"Mutual: {p.get('mutual','—')}"
            self.tree_pagos.insert("", "end", iid=str(i), values=(
                medio,
                money(p["importe"]),
                comprobante,
            ))

    def _agregar_pago(self):
        if self._sin_permiso_ventas():
            return
        total = self._total_ticket()
        if total <= 0:
            messagebox.showwarning(
                "Ticket vacío",
                "Agregá al menos un producto con + AGREGAR AL TICKET antes "
                "de cargar cómo se pagó.",
                parent=self,
            )
            return
        # Con el botón siempre se intenta cargar la fila: si no se cargó
        # importe, toma lo que falta para cerrar el total.
        pago = self._pago_pendiente(total, avisos=True, forzar=True)
        if pago is None:
            return
        self._pagos.append(pago)
        self._pagos_fijos = False
        self._cargando = True
        try:
            self.var_importe.set("")
            self.var_comprobante.set("")
            self.var_mutual.set("")
        finally:
            self._cargando = False
        self._pintar_pagos()
        self._recalcular()

    def _quitar_pago(self):
        sel = self.tree_pagos.selection()
        if not sel:
            messagebox.showwarning("Ticket",
                                   "Elegí un medio de pago de la lista para "
                                   "quitarlo.", parent=self)
            return
        for iid in sorted((int(i) for i in sel), reverse=True):
            if 0 <= iid < len(self._pagos):
                del self._pagos[iid]
        self._pagos_fijos = False
        self._pintar_pagos()
        self._recalcular()

    def _pago_seleccionado(self, _=None):
        """Clic en un medio de pago: pasa a la fila para corregirlo."""
        if self._cargando:
            return
        sel = self.tree_pagos.selection()
        if not sel:
            return
        i = int(sel[0])
        if not 0 <= i < len(self._pagos):
            return
        pago = self._pagos.pop(i)
        self._cargando = True
        try:
            self.combo_medio.set(pago["medio"])
            self.var_importe.set(money(pago["importe"]).replace("$", ""))
            self.var_comprobante.set(pago.get("comprobante") or "")
            self.var_mutual.set(pago.get("mutual") or "")
        finally:
            self._cargando = False
        self._pagos_fijos = False
        self._pintar_pagos()
        self._medio_cambiado()
        self._recalcular()
        self.ent_importe.focus_set()

    def _actualizar_estado_pago(self):
        """Aviso de cuadre: EFECTIVO + TARJETA + TRANSFERENCIA = TOTAL."""
        total = self._total
        if total <= 0:
            self.lbl_pago.config(text="Cargá el primer producto para armar el "
                                      "ticket.",
                                 fg=st.TEXTO_SUAVE)
            return
        pagado = sum(p["importe"] for p in self._pagos)
        pendiente = (self._pago_pendiente(total)
                     if self._pago_aplica() else None)
        if pendiente:
            pagado += pendiente["importe"]
        resto = total - pagado
        if abs(resto) < 0.01:
            texto = f"PAGOS = TOTAL: {money(pagado)} — listo para registrar"
            color = st.VERDE_OSCURO
        elif not self._pagos and pendiente is None:
            texto = "Falta indicar cómo se paga este ticket."
            color = st.ROJO
        elif resto > 0:
            texto = (f"FALTAN {money(resto)} para completar el total "
                     f"({money(total)})")
            color = st.ROJO
        else:
            texto = f"LOS PAGOS SUPERAN EL TOTAL EN {money(-resto)}"
            color = st.ROJO
        self.lbl_pago.config(text=texto, fg=color)

    def _datos_form(self):
        """Valida la fila de producto y el medio de pago pendiente.
        Devuelve (producto, cantidad, precio, medio, comprobante, cliente)
        o None si algo falta (y avisa qué)."""
        line = self._datos_linea()
        if not line:
            return None
        producto, cantidad, precio = line
        medio = self.combo_medio.get()
        comprobante = self.var_comprobante.get().strip()
        cliente = self.var_cliente.get().strip()
        if medio not in db.MEDIOS_PAGO:
            messagebox.showwarning("Venta", "Seleccioná el medio de pago.",
                                   parent=self)
            return None
        if self._pago_aplica():
            # Permiso individual por medio de pago (movimientos de dinero)
            permiso_medio = db.MEDIO_PERMISO.get(medio)
            if permiso_medio and not db.puede(permiso_medio):
                messagebox.showerror(
                    "Sin permisos",
                    "Tu usuario no tiene permiso para registrar cobros con "
                    f"{medio}.",
                    parent=self,
                )
                return None
            txt = self.var_importe.get().strip()
            if txt:
                importe = parse_numero(txt)
                if importe is None or importe <= 0:
                    messagebox.showwarning(
                        "Importe",
                        f"Ingresá un importe válido para {medio}.",
                        parent=self,
                    )
                    return None
            # Regla: toda transferencia necesita número de comprobante
            if medio == "Transferencia" and not comprobante:
                messagebox.showerror(
                    "Falta el comprobante",
                    "Para registrar una venta paga con TRANSFERENCIA es "
                    "obligatorio ingresar el N° de comprobante.\n\n"
                    "Ingresá el número y volvé a presionar "
                    "«REGISTRAR VENTA».",
                    parent=self,
                )
                self.ent_comprobante.focus_set()
                return None
        return producto, cantidad, precio, medio, comprobante, cliente

    def _recalcular(self, *_):
        self._total = self._total_ticket()
        self.lbl_total.config(text=money(self._total))
        self._actualizar_desglose()
        self._actualizar_importe()
        self._actualizar_estado_pago()

    def _suma_items(self):
        return sum(i["cantidad"] * i["precio_unitario"] for i in self._items)

    def _actualizar_desglose(self):
        """Explica de qué está hecho el total (nada de números mágicos)."""
        if not self._items:
            self.lbl_desglose.config(text="", fg=st.TEXTO_SUAVE)
            return
        suma = self._suma_items()
        if self._linea_tocada:
            texto = (f"En la lista {money(suma)}  +  fila cargada "
                     f"{money(self._total_linea())} (entra al registrar)")
            color = st.AMBAR
        else:
            texto = f"En la lista {money(suma)} (la fila de arriba ya está sumada)"
            color = st.TEXTO_SUAVE
        self.lbl_desglose.config(text=texto, fg=color)

    def _actualizar_importe(self):
        """Etiqueta del importe: qué se cobra si lo dejan vacío / cuánto falta."""
        pagado = sum(p["importe"] for p in self._pagos)
        if self._pagos_fijos and len(self._pagos) == 1:
            # Único medio de la venta editada: su importe acompaña al total
            pagado = self._total
        base = self._total - pagado
        txt = self.var_importe.get().strip()
        if not txt:
            if base > 0.01:
                texto = f"IMPORTE — vacío = {money(base)}"
                color = st.TEXTO_SUAVE
            else:
                texto = "IMPORTE"
                color = st.TEXTO_SUAVE
        else:
            importe = parse_numero(txt) or 0
            resto = base - importe
            if resto > 0.01:
                texto = f"IMPORTE — faltan {money(resto)}"
                color = st.ROJO
            elif resto < -0.01:
                texto = f"IMPORTE — sobran {money(-resto)}"
                color = st.ROJO
            else:
                texto = "IMPORTE — cierra con el total"
                color = st.VERDE_OSCURO
        self.lbl_importe.config(text=texto, fg=color)

    def _registrar(self):
        if self._sin_permiso_ventas():
            return
        caja = self.app.caja_actual()
        if not caja:
            return
        if caja["estado"] != "abierta":
            messagebox.showerror("Caja cerrada",
                                 "La caja está cerrada y bloqueada. "
                                 "Reabrila desde Historial para registrar ventas.",
                                 parent=self)
            return
        if not db.apertura_de(caja["id"]):
            messagebox.showerror(
                "Caja sin abrir",
                "La caja todavía no fue abierta.\n"
                "Andá a la pantalla Inicio y presioná ABRIR CAJA "
                "para registrar quién la abre y con cuánto fondo.",
                parent=self)
            return
        datos = self._datos_form()
        if not datos:
            return
        producto, cantidad, precio, medio, comprobante, cliente = datos

        # Productos: lo agregado + la fila cargada (si se modificó o está vacía)
        items = [dict(i) for i in self._items]
        if not items or self._linea_tocada:
            items.append({
                "producto_id": producto["id"],
                "cantidad": cantidad,
                "precio_unitario": precio,
                "producto": producto["nombre"],
            })
        total = sum(i["cantidad"] * i["precio_unitario"] for i in items)

        # Medios de pago: los agregados + la fila cargada
        pagos = [dict(p) for p in self._pagos]
        if (self._pagos_fijos and len(pagos) == 1
                and not self.var_importe.get().strip()):
            # Único medio de pago de la venta: su importe acompaña al total
            pagos[0]["importe"] = total
        fila_activa = self._pago_aplica()
        pendiente = self._pago_pendiente(total, avisos=True)
        if pendiente is None and fila_activa:
            # Ya avisó el motivo (importe inválido, comprobante, permiso)
            return
        if pendiente is not None:
            pagos.append(pendiente)
        if not pagos:
            messagebox.showwarning("Falta el pago",
                                   "Indicá cómo pagó el cliente antes de "
                                   "registrar la venta.", parent=self)
            return

        # El cobro tiene que cerrar con el total: si falta, ofrecemos completarlo
        resto = round(total - sum(p["importe"] for p in pagos), 2)
        if abs(resto) >= 0.01:
            if resto <= 0:
                messagebox.showerror(
                    "No se pudo registrar",
                    f"Los cobros superan el total en {money(-resto)}.",
                    parent=self)
                return
            ultimo = pagos[-1]["medio"]
            if not messagebox.askyesno(
                    "La venta no cierra",
                    f"El ticket vale {money(total)} y los cobros cargados "
                    f"suman {money(total - resto)}.\n\n"
                    f"FALTAN {money(resto)}.\n\n"
                    f"¿Los agregamos a {ultimo} para cerrar la venta?",
                    parent=self):
                messagebox.showerror(
                    "No se pudo registrar",
                    f"FALTAN {money(resto)} para completar el total de "
                    f"{money(total)}.\n\nAgregá el medio de pago que falta o "
                    "corregí el importe y volvé a presionar "
                    "«REGISTRAR VENTA».",
                    parent=self)
                return
            for p in reversed(pagos):
                if p["medio"] == ultimo:
                    p["importe"] = round(p["importe"] + resto, 2)
                    break

        linea = db.texto_items(items)
        detalle = f"{linea}\nFormas de pago: {db.texto_pagos(pagos)}"

        if self._editando_id is not None:
            try:
                ticket = db.actualizar_ticket(self._editando_id, items, pagos,
                                              cliente)
            except ValueError as e:
                messagebox.showerror("No se pudo guardar", str(e), parent=self)
                return
            numero = ticket["id"]
            self._limpiar_edicion()
            messagebox.showinfo("Venta corregida",
                                f"Venta #{numero} actualizada:\n{detalle}\n"
                                f"Total: {money(ticket['total'])}",
                                parent=self)
        else:
            try:
                ticket = db.registrar_ticket(caja["id"], items, pagos, cliente)
            except ValueError as e:
                messagebox.showerror("No se pudo guardar", str(e), parent=self)
                return
            if ticket.get("comprobante"):
                detalle += f"\nComprobante N°: {ticket['comprobante']}"
            if cliente:
                detalle += f"\nCliente: {cliente}"
            self._limpiar_trabajo()
            messagebox.showinfo("Venta registrada",
                                f"{detalle}\nTotal: {money(ticket['total'])}",
                                parent=self)

        self._medio_cambiado()
        self._recalcular()
        self.app.refrescar_todo()

    def _editar(self):
        if self._sin_permiso_ventas():
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Editar",
                                   "Seleccioná una venta de la lista para editarla.",
                                   parent=self)
            return
        venta = db.venta_por_id(int(sel[0]))
        if not venta:
            return

        self._cargando = True
        try:
            self._items = []
            self._pagos = [dict(p) for p in venta.get("pagos") or []]
            self.var_importe.set("")
            self.var_comprobante.set("")
            self.var_cliente.set(venta.get("cliente") or "")

            items = venta.get("items") or []
            if len(items) == 1:
                # Un solo producto: se edita directo en la fila
                it = items[0]
                for i, p in enumerate(self._productos):
                    if p["id"] == it["producto_id"]:
                        self.combo_producto.current(i)
                        break
                self.var_cantidad.set(str(it["cantidad"]))
                self.var_precio.set(money(it["precio_unitario"]).replace("$", ""))
            elif items:
                # Varios productos: van a la lista del ticket
                for it in items:
                    self._items.append({
                        "producto_id": it["producto_id"],
                        "cantidad": it["cantidad"],
                        "precio_unitario": it["precio_unitario"],
                        "producto": it.get("producto"),
                    })
                if self._productos:
                    self.combo_producto.current(0)
                    self.var_cantidad.set("1")
                    self.var_precio.set(
                        money(self._productos[0]["precio"]).replace("$", ""))
            if venta.get("pagos"):
                self.combo_medio.set(venta["pagos"][0]["medio"])
        finally:
            self._cargando = False

        self._linea_tocada = False
        # Si la venta tenía UN solo medio de pago, su importe sigue al total
        self._pagos_fijos = len(self._pagos) == 1
        self._editando_id = venta["id"]
        self._pintar_items()
        self._pintar_pagos()
        self._medio_cambiado()
        self._recalcular()

        self.btn_registrar.config(text="GUARDAR CAMBIOS", bg=st.AMBAR)
        self.lbl_info.config(
            text=f"Editando venta #{venta['id']} — modificá lo necesario y "
                 f"presioná GUARDAR CAMBIOS.",
            fg=st.AMBAR,
        )
        self.btn_cancelar.pack(side="left", padx=(10, 0))

    def _cancelar_edicion(self):
        self._limpiar_edicion()
        self.app.refrescar_todo()

    def _limpiar_trabajo(self):
        """Deja el formulario listo para la próxima venta."""
        self._items = []
        self._pagos = []
        self._linea_tocada = False
        self._pagos_fijos = False
        self._cargando = True
        try:
            self.var_cantidad.set("1")
            self.var_importe.set("")
            self.var_comprobante.set("")
            self.var_cliente.set("")
        finally:
            self._cargando = False
        self._pintar_items()
        self._pintar_pagos()

    def _limpiar_edicion(self):
        self._editando_id = None
        self.btn_registrar.config(text="REGISTRAR VENTA", bg=st.VERDE)
        self.lbl_info.config(fg=st.TEXTO)
        self.btn_cancelar.pack_forget()
        self._limpiar_trabajo()

    def _caja_operativa(self, accion):
        """True (y avisa) si no se puede operar sobre la caja actual."""
        caja = self.app.caja_actual()
        if caja and caja["estado"] == "abierta":
            return True
        messagebox.showerror("Caja cerrada",
                             f"No se pueden {accion} de una caja cerrada.",
                             parent=self)
        return False

    def _eliminar(self):
        if self._sin_permiso_ventas():
            return
        if not self._caja_operativa("eliminar ventas"):
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Eliminar",
                "Seleccioná una o más ventas de la lista "
                "(Ctrl o Shift + clic para elegir varias).",
                parent=self)
            return
        ids = [int(i) for i in sel]
        if len(ids) == 1:
            texto = "¿Eliminar la venta seleccionada?"
        else:
            texto = (f"¿Eliminar las {len(ids)} ventas seleccionadas?\n"
                     "No se puede deshacer.")
        if not messagebox.askyesno("Eliminar ventas", texto, parent=self):
            return
        db.eliminar_ventas(ids)
        if self._editando_id in ids:
            self._limpiar_edicion()
        self.app.refrescar_todo()

    def _vaciar_caja(self):
        """Borra de una sola vez todo lo cargado en la caja del día."""
        if self._sin_permiso_ventas():
            return
        if not self._caja_operativa("eliminar ventas"):
            return
        ids = [int(i) for i in self.tree.get_children()]
        if not ids:
            messagebox.showwarning("Borrar caja",
                                   "No hay ventas cargadas en esta caja.",
                                   parent=self)
            return
        if not messagebox.askyesno(
                "Borrar toda la caja",
                f"¿Eliminar las {len(ids)} ventas de esta caja?\n"
                "Se borra todo lo cargado. No se puede deshacer.",
                parent=self):
            return
        db.eliminar_ventas(ids)
        self._limpiar_edicion()
        self.app.refrescar_todo()

    # ------------------------------------------------------------- refresco
    def refresh(self):
        caja = self.app.caja_actual()
        if not caja:
            return

        apertura = db.apertura_de(caja["id"])
        operativa = caja["estado"] == "abierta" and apertura is not None
        sin_abrir = caja["estado"] == "abierta" and apertura is None
        if operativa:
            estado_txt = "abierta"
        elif sin_abrir:
            estado_txt = "sin abrir"
        else:
            estado_txt = "cerrada y bloqueada"
        self.lbl_sub.config(
            text=f"Caja del {fecha_larga(caja['fecha'])} — {estado_txt}"
        )

        if operativa:
            self.lbl_bloqueada.pack_forget()
        else:
            self.lbl_bloqueada.pack(fill="x", padx=28, pady=(8, 0), after=self._cab)
            if sin_abrir:
                self.lbl_bloqueada.set(
                    text="CAJA SIN ABRIR: presioná ABRIR CAJA en la pantalla "
                         "Inicio para registrar el monto inicial y poder "
                         "cargar ventas."
                )
            else:
                self.lbl_bloqueada.set(
                    text="CAJA CERRADA: no se pueden registrar ni eliminar ventas. "
                         "Para modificar, usá la reapertura de caja en Historial."
                )

        # Estado de los controles
        self.combo_producto.configure(state="readonly" if operativa else "disabled")
        self.spin_cantidad.configure(state="normal" if operativa else "disabled")
        self.ent_precio.configure(state="normal" if operativa else "disabled")
        self.ent_cliente.configure(state="normal" if operativa else "disabled")
        self.combo_medio.configure(state="readonly" if operativa else "disabled")
        self.ent_importe.configure(state="normal" if operativa else "disabled")
        self.ent_comprobante.configure(state="normal" if operativa else "disabled")
        self.btn_registrar.config(state="normal" if operativa else "disabled",
                                  bg=st.VERDE if operativa else "#a3d9b5")
        self.btn_agregar_item.config(state="normal" if operativa else "disabled",
                                     bg=st.ACENTO if operativa else "#a9c4f7")
        self.btn_agregar_pago.config(state="normal" if operativa else "disabled",
                                     bg=st.BARRA if operativa else "#8b93a5")
        self.btn_quitar_item.config(state="normal" if operativa else "disabled")
        self.btn_quitar_pago.config(state="normal" if operativa else "disabled")
        self.btn_eliminar.config(state="normal" if operativa else "disabled",
                                 bg=st.ROJO if operativa else "#f0a8a8")
        self.btn_vaciar.config(state="normal" if operativa else "disabled",
                               bg="#7f1d1d" if operativa else "#d9a3a3")
        modo_lista = "extended" if operativa else "none"
        self.tree_items.configure(selectmode=modo_lista)
        self.tree_pagos.configure(selectmode=modo_lista)

        # Solo se ofrecen los medios de pago que el usuario puede registrar
        medios = self._medios_permitidos()
        self.combo_medio["values"] = medios
        if operativa and medios and self.combo_medio.get() not in medios:
            self.combo_medio.set(medios[0])
            self._medio_cambiado()

        # Productos
        self._cargando = True
        try:
            self._productos = db.productos()
            nombres = [p["nombre"] for p in self._productos]
            seleccion_previa = self.combo_producto.get()
            self.combo_producto["values"] = nombres
            if seleccion_previa in nombres:
                self.combo_producto.set(seleccion_previa)
            elif nombres:
                self.combo_producto.current(0)
                self._producto_cambiado()
        finally:
            self._cargando = False

        # Listado de ventas
        self.tree.delete(*self.tree.get_children())
        r = db.resumen(caja["id"])
        for v in r["ventas"]:
            hora = v["fecha_hora"].split(" ")[1][:5] if v["fecha_hora"] else ""
            comprobante = v.get("comprobante") or "—"
            self.tree.insert(
                "", "end", iid=str(v["id"]),
                tags=("cerrada",) if not operativa else (),
                values=(
                    f"#{v['id']}",
                    hora,
                    v.get("producto") or "—",
                    v["cantidad"],
                    v.get("cliente") or "—",
                    v.get("medios_txt") or v.get("medio") or "—",
                    comprobante,
                    money(v["total"]),
                    v.get("cajero") or "—",
                ),
            )
        if not operativa:
            self.tree.tag_configure("cerrada", foreground=st.TEXTO_SUAVE)

        # Las listas del ticket se repintan con el trabajo en curso
        self._pintar_items()
        self._pintar_pagos()

        self.lbl_info.config(
            text=f"Garrafas vendidas: {r['total_garrafas']}    |    "
                 f"Total del día: {money(r['total_vendido'])}    |    "
                 f"Ventas: {r['cantidad_ventas']}"
        )

        # Si la venta que se estaba editando ya no existe, se cancela la edición
        if self._editando_id is not None:
            if db.venta_por_id(self._editando_id) is None:
                self._limpiar_edicion()
            else:
                self.lbl_info.config(
                    text=f"Editando venta #{self._editando_id} — modificá lo "
                         f"necesario y presioná GUARDAR CAMBIOS.",
                    fg=st.AMBAR,
                )
                self.btn_registrar.config(text="GUARDAR CAMBIOS", bg=st.AMBAR)
                if not self.btn_cancelar.winfo_ismapped():
                    self.btn_cancelar.pack(side="left", padx=(10, 0))
        self.lbl_pie.config(
            text=f"Efectivo {money(r['efectivo'])}  •  "
                 f"Transferencia {money(r['transferencias'])} "
                 f"({r['n_transferencias']})  •  "
                 f"Tarjetas {money(r['debito'] + r['credito'])} "
                 f"(Débito {money(r['debito'])} • "
                 f"Crédito {money(r['credito'])})"
        )
        self._medio_cambiado()
        self._recalcular()
