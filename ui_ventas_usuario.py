# -*- coding: utf-8 -*-
"""Panel de Ventas — Módulo USUARIO.

Venta sin clientes registrados: el cliente se escribe al vuelo (nombre y
apellido). Precio unitario a mano (como en MOSTRADOR). Pagos múltiples
permitidos (mismo medio repetible). La venta queda identificada como
modulo='USUARIO' para estadísticas por sector.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
import uuid

import database as db
import estilos as st
import iconos as ic
from widgets_figma import Tarjeta, Btn
from ui_comun import tarjeta as uc_tarjeta
from util import money, parse_numero


# Solo letras, tildes, ñ, espacios, apóstrofe y guion; 1 a 60 caracteres
_RE_NOMBRE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s'-]{1,60}$")


class VentasUsuarioPanel(tk.Frame):
    """Ventas del módulo USUARIO (sin clientes registrados)."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._items = []          # {"producto_id", "nombre", "cantidad",
                                  #  "precio_unitario", "subtotal"}
        self._pagos = []          # {"medio", "importe", "comprobante"}
        self._nombre = ""
        self._apellido = ""
        self._total = 0.0
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        PX = 28
        MUTED = st.TEXTO_SUAVE
        cont = st.contenido_scrollable(self)
        self.contenido = cont

        # ---------------- Cabecera ----------------
        cab = tk.Frame(cont, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 4))
        tk.Label(cab, text="Ventas — Módulo USUARIO", bg=st.FONDO,
                 fg=st.TEXTO, font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(cab, text="Venta sin cliente registrado. Precio unitario a "
                 "mano. Pagos múltiples permitidos. Queda identificada como "
                 "sector USUARIO en estadísticas.",
                 bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 11)).pack(anchor="w")

        # Aviso de caja cerrada
        self.lbl_bloqueada = tk.Label(cont, text="", bg="#FDEEEE",
                                      fg="#9B1C1C", font=(st.FUENTE, 10))
        self.lbl_bloqueada.pack(fill="x", padx=PX, pady=(0, 6))

        # ---------------- Paso 1: Cliente (nombre y apellido) ----------------
        t1, c1, _h1 = uc_tarjeta(cont, "Paso 1: Nombre y apellido del cliente",
                            "user", padx=PX, pady=14)
        t1.pack(fill="x", padx=PX, pady=(14, 0))
        fila = tk.Frame(c1, bg=st.TARJETA)
        fila.pack(fill="x", pady=4)
        self.var_nombre = tk.StringVar()
        self.var_apellido = tk.StringVar()

        c_n = tk.Frame(fila, bg=st.TARJETA)
        c_n.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(c_n, text="NOMBRE (obligatorio)", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.ent_nombre = tk.Entry(c_n, textvariable=self.var_nombre,
                                   font=(st.FUENTE, 11), relief="flat", bd=0,
                                   bg="#FFFFFF", highlightthickness=1,
                                   highlightbackground="#D9E0EC",
                                   highlightcolor=st.ACENTO)
        self.ent_nombre.pack(fill="x", pady=(3, 0), ipady=6)

        c_a = tk.Frame(fila, bg=st.TARJETA)
        c_a.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(c_a, text="APELLIDO (obligatorio)", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.ent_apellido = tk.Entry(c_a, textvariable=self.var_apellido,
                                     font=(st.FUENTE, 11), relief="flat",
                                     bd=0, bg="#FFFFFF", highlightthickness=1,
                                     highlightbackground="#D9E0EC",
                                     highlightcolor=st.ACENTO)
        self.ent_apellido.pack(fill="x", pady=(3, 0), ipady=6)
        self.var_nombre.trace_add("write", self._validar_cliente)
        self.var_apellido.trace_add("write", self._validar_cliente)
        self.lbl_cliente_ok = tk.Label(c1, text="", bg=st.TARJETA,
                                       fg="#2E7D32", font=(st.FUENTE, 9))
        self.lbl_cliente_ok.pack(anchor="w", pady=(4, 0))

        # ---------------- Paso 2: Productos y precio ----------------
        t2, c2, _h2 = uc_tarjeta(cont, "Paso 2: Productos y precio unitario",
                            "cart", padx=PX, pady=14)
        t2.pack(fill="x", padx=PX, pady=(14, 0))
        grid = tk.Frame(c2, bg=st.TARJETA)
        grid.pack(fill="x", pady=4)
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform="campo")

        def campo(col, etiqueta, fila=0):
            celda = tk.Frame(grid, bg=st.TARJETA)
            celda.grid(row=fila, column=col, sticky="nsew",
                       padx=(0 if col == 0 else 8,
                             0 if col == 3 else 8),
                       pady=(0, 10))
            lbl = tk.Label(celda, text=etiqueta, bg=st.TARJETA, fg=MUTED,
                           font=(st.FUENTE, 9, "bold"), anchor="w",
                           justify="left")
            lbl.pack(fill="x")
            celda.bind("<Configure>", lambda e, l=lbl: l.configure(
                wraplength=max(60, e.width - 2)))
            return celda

        c_prod = campo(0, "PRODUCTO", 0)
        self.combo_producto = ttk.Combobox(c_prod, state="readonly",
                                           width=26, font=(st.FUENTE, 11))
        self.combo_producto.pack(fill="x", pady=(4, 0))
        self.combo_producto.bind("<<ComboboxSelected>>",
                                 self._producto_cambiado)

        c_cant = campo(1, "CANTIDAD", 0)
        self.var_cantidad = tk.StringVar(value="1")
        self.spin_cantidad = ttk.Spinbox(c_cant, from_=1, to=9999, width=8,
                                         textvariable=self.var_cantidad,
                                         font=(st.FUENTE, 11),
                                         justify="center",
                                         command=self._linea_modificada)
        self.spin_cantidad.pack(fill="x", pady=(4, 0))
        self.var_cantidad.trace_add("write", self._linea_modificada)

        c_precio = campo(2, "PRECIO UNITARIO (a mano)", 0)
        self.var_precio = tk.StringVar(value="")
        self.ent_precio = tk.Entry(c_precio, textvariable=self.var_precio,
                                   font=(st.FUENTE, 11), relief="flat", bd=0,
                                   bg="#FFFFFF", highlightthickness=1,
                                   highlightbackground="#D9E0EC",
                                   highlightcolor=st.ACENTO)
        self.ent_precio.pack(fill="x", pady=(4, 0), ipady=6)
        self.var_precio.trace_add("write", self._linea_modificada)

        c_agregar = campo(3, "AGREGAR", 0)
        btn_agregar = Btn(c_agregar, text="+ AGREGAR", command=self._agregar,
                          bg=st.VERDE, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
                          padx=16, pady=6)
        btn_agregar.pack(fill="x", pady=(24, 0))

        self.lbl_precio_info = tk.Label(c2, text="", bg=st.TARJETA, fg=MUTED,
                                        font=(st.FUENTE, 9))
        self.lbl_precio_info.pack(anchor="w")

        # ---------------- Paso 3: Pagos múltiples ----------------
        t3, c3, _h3 = uc_tarjeta(cont, "Paso 3: Pagos (uno o más)",
                            "credit-card", padx=PX, pady=14)
        t3.pack(fill="x", padx=PX, pady=(14, 0))

        grid3 = tk.Frame(c3, bg=st.TARJETA)
        grid3.pack(fill="x", pady=4)
        for c in range(3):
            grid3.columnconfigure(c, weight=1, uniform="pago")

        cp = tk.Frame(grid3, bg=st.TARJETA)
        cp.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        tk.Label(cp, text="MEDIO DE PAGO", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.combo_medio = ttk.Combobox(cp, state="readonly", width=18,
                                        values=["Efectivo", "Transferencia",
                                                "Tarjeta de débito",
                                                "Tarjeta de crédito"],
                                        font=(st.FUENTE, 11))
        self.combo_medio.set("Efectivo")
        self.combo_medio.pack(fill="x", pady=(4, 0))

        ci = tk.Frame(grid3, bg=st.TARJETA)
        ci.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=(0, 10))
        tk.Label(ci, text="IMPORTE", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.var_importe = tk.StringVar(value="")
        self.ent_importe = tk.Entry(ci, textvariable=self.var_importe,
                                    font=(st.FUENTE, 11), relief="flat", bd=0,
                                    bg="#FFFFFF", highlightthickness=1,
                                    highlightbackground="#D9E0EC",
                                    highlightcolor=st.ACENTO)
        self.ent_importe.pack(fill="x", pady=(4, 0), ipady=6)
        self.var_importe.trace_add("write", self._actualizar_falta)

        cc = tk.Frame(grid3, bg=st.TARJETA)
        cc.grid(row=0, column=2, sticky="nsew", padx=(0, 8), pady=(0, 10))
        tk.Label(cc, text="N° COMPROBANTE (Transferencia)", bg=st.TARJETA,
                 fg=MUTED, font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.var_comprobante = tk.StringVar(value="")
        self.ent_comprobante = tk.Entry(cc, textvariable=self.var_comprobante,
                                        font=(st.FUENTE, 11), relief="flat",
                                        bd=0, bg="#FFFFFF", highlightthickness=1,
                                        highlightbackground="#D9E0EC",
                                        highlightcolor=st.ACENTO)
        self.ent_comprobante.pack(fill="x", pady=(4, 0), ipady=6)

        btn_pagos = tk.Frame(c3, bg=st.TARJETA)
        btn_pagos.pack(fill="x", pady=(4, 0))
        Btn(btn_pagos, text="+ AGREGAR PAGO", command=self._agregar_pago,
            bg=st.VERDE, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=16, pady=6).pack(side="left")
        self.btn_precargar = Btn(btn_pagos, text="Precargar total",
                                 command=self._precargar_total,
                                 bg="#64748B", fg="#ffffff",
                                 font=(st.FUENTE, 10, "bold"),
                                 padx=16, pady=6)
        self.btn_precargar.pack(side="left", padx=(10, 0))

        # Lista de pagos cargados
        self.tree_pagos = ttk.Treeview(c3, columns=("medio", "importe",
                                                    "comprobante"),
                                       show="headings", height=4)
        for col, w, anchor in (("medio", 160, "w"), ("importe", 120, "e"),
                               ("comprobante", 160, "w")):
            self.tree_pagos.heading(col, text=col.title())
            self.tree_pagos.column(col, width=w, anchor=anchor)
        self.tree_pagos.pack(fill="both", expand=True, pady=(6, 4))
        self.tree_pagos.bind("<Delete>", lambda e: self._quitar_pago())
        self.tree_pagos.bind("<BackSpace>", lambda e: self._quitar_pago())

        # ---------------- Resumen y total ----------------
        t4, c4, _h4 = uc_tarjeta(cont, "Resumen del ticket", "receipt",
                            padx=PX, pady=14)
        t4.pack(fill="x", padx=PX, pady=(14, 0))

        self.tree_items = ttk.Treeview(c4, columns=("producto", "cantidad",
                                                    "precio", "subtotal"),
                                       show="headings", height=6)
        for col, w, anchor in (("producto", 260, "w"), ("cantidad", 80, "center"),
                               ("precio", 110, "e"), ("subtotal", 120, "e")):
            self.tree_items.heading(col, text=col.title())
            self.tree_items.column(col, width=w, anchor=anchor)
        self.tree_items.pack(fill="both", expand=True, pady=(6, 4))

        caja_res = tk.Frame(c4, bg=st.TARJETA)
        caja_res.pack(fill="x", pady=(4, 0))
        for col, texto in (("total", "TOTAL:"), ("pagado", "PAGADO:"),
                           ("saldo", "SALDO RESTANTE:")):
            f = tk.Frame(caja_res, bg=st.TARJETA)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=texto, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 10, "bold"), width=16).pack(side="left")
            lbl = tk.Label(f, text="$0", bg=st.TARJETA, fg=st.TEXTO,
                           font=(st.FUENTE, 11), anchor="e")
            lbl.pack(side="right")
            setattr(self, f"lbl_{col}", lbl)

        self.lbl_estado_falta = tk.Label(c4, text="", bg=st.TARJETA,
                                  fg="#9B1C1C", font=(st.FUENTE, 10, "bold"),
                                  anchor="e")
        self.lbl_estado_falta.pack(anchor="e", pady=(2, 0))

        # ---------------- Acciones ----------------
        acciones = tk.Frame(c4, bg=st.TARJETA)
        acciones.pack(fill="x", pady=(10, 0))
        self.btn_confirmar = Btn(acciones, text="CONFIRMAR VENTA",
                                 command=self._confirmar,
                                 bg=st.VERDE, fg="#ffffff",
                                 font=(st.FUENTE, 11, "bold"),
                                 padx=24, pady=12, state="disabled")
        self.btn_confirmar.pack(side="left")
        Btn(acciones, text="CANCELAR TODO", command=self._cancelar_todo,
            bg="#64748B", fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=18, pady=10).pack(side="left", padx=(10, 0))

        self.lbl_msg = tk.Label(c4, text="", bg=st.TARJETA, fg=st.TEXTO,
                                font=(st.FUENTE, 10))
        self.lbl_msg.pack(anchor="w", pady=(6, 0))

    # ------------------------------------------------------------------ helpers
    def _validar_cliente(self, *args):
        nombre = (self.var_nombre.get() or "").strip()
        apellido = (self.var_apellido.get() or "").strip()
        ok_n = bool(nombre) and bool(_RE_NOMBRE.match(nombre))
        ok_a = bool(apellido) and bool(_RE_NOMBRE.match(apellido))
        if ok_n and ok_a:
            self.lbl_cliente_ok.config(
                text=f"Cliente: {nombre} {apellido}",
                fg="#2E7D32")
            self._nombre = nombre
            self._apellido = apellido
        else:
            self.lbl_cliente_ok.config(
                text="Nombre y apellido obligatorios "
                     "(solo letras, espacios, tildes, ñ, apóstrofe y guion)",
                fg="#9B1C1C")
            self._nombre = ""
            self._apellido = ""
        self._actualizar_estado_confirmar()

    def _cargar_productos(self):
        productos = db.productos(solo_activos=True)
        self.combo_producto["values"] = [f"{p['id']} — {p['nombre']}"
                                         for p in productos]
        self._productos_map = {f"{p['id']} — {p['nombre']}": p
                               for p in productos}
        self.combo_producto.set("")
        self.var_precio.set("")
        self.lbl_precio_info.config(text="")

    def _producto_cambiado(self, _event):
        valor = self.combo_producto.get()
        if not valor or not hasattr(self, "_productos_map"):
            return
        p = self._productos_map.get(valor)
        if not p:
            return
        self.lbl_precio_info.config(
            text=f"Producto: {p['nombre']} — precio a mano",
            fg=st.TEXTO)
        self._linea_modificada()

    def _linea_modificada(self, *args):
        try:
            cantidad = int(self.var_cantidad.get() or 1)
            if cantidad <= 0:
                cantidad = 1
                self.var_cantidad.set("1")
        except ValueError:
            cantidad = 1
            self.var_cantidad.set("1")
        try:
            precio = parse_numero(self.var_precio.get())
            if precio is None:
                precio = 0.0
        except ValueError:
            precio = 0.0
        subtotal = cantidad * precio
        self.lbl_precio_info.config(
            text=f"Subtotal: {money(subtotal)}")

    def _agregar(self):
        if not self._nombre or not self._apellido:
            messagebox.showwarning("Cliente",
                                   "Completá nombre y apellido válidos.",
                                   parent=self)
            return
        valor = self.combo_producto.get()
        if not valor or not hasattr(self, "_productos_map"):
            messagebox.showwarning("Producto", "Seleccioná un producto.",
                                   parent=self)
            return
        p = self._productos_map[valor]
        pid = p["id"]
        try:
            cantidad = int(self.var_cantidad.get() or 1)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cantidad", "Cantidad inválida.", parent=self)
            return
        precio = parse_numero(self.var_precio.get())
        if precio is None or precio <= 0:
            messagebox.showerror("Precio", "Precio unitario inválido.",
                                 parent=self)
            return

        subtotal = cantidad * precio
        self._items.append({
            "producto_id": pid,
            "nombre": p["nombre"],
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": subtotal,
        })
        self._actualizar_items()
        self.combo_producto.set("")
        self.var_precio.set("")
        self.var_cantidad.set("1")
        self.lbl_precio_info.config(text="")

    def _actualizar_items(self):
        for i in self.tree_items.get_children():
            self.tree_items.delete(i)
        self._total = 0.0
        for it in self._items:
            self.tree_items.insert("", "end", values=(
                it["nombre"], it["cantidad"],
                money(it["precio_unitario"]), money(it["subtotal"])))
            self._total += it["subtotal"]
        self.lbl_total.config(text=money(self._total))
        self._actualizar_falta()
        self._actualizar_estado_confirmar()

    def _actualizar_falta(self, *args):
        try:
            pagado = parse_numero(self.var_importe.get()) or 0.0
        except ValueError:
            pagado = 0.0
        falta = self._total - pagado
        self.lbl_pagado.config(text=money(pagado))
        self.lbl_saldo.config(text=money(falta))
        if falta > 0.001:
            self.lbl_estado_falta.config(text=f"Falta cobrar: {money(falta)}",
                                  fg="#9B1C1C")
        elif falta < -0.001:
            self.lbl_estado_falta.config(text=f"Sobrante: {money(-falta)}",
                                  fg="#9B1C1C")
        else:
            self.lbl_estado_falta.config(text="Pagado exactamente", fg="#2E7D32")

    def _agregar_pago(self):
        medio = self.combo_medio.get()
        importe = parse_numero(self.var_importe.get())
        if importe is None or importe <= 0:
            messagebox.showerror("Importe", "Importe de pago inválido.",
                                 parent=self)
            return
        if medio == "Transferencia" and not self.var_comprobante.get().strip():
            messagebox.showerror("Comprobante",
                                 "La transferencia requiere n° de comprobante.",
                                 parent=self)
            return
        pagado_actual = sum(p["importe"] for p in self._pagos)
        if pagado_actual + importe > self._total + 0.001:
            messagebox.showerror("Excede el total",
                                 "La suma de pagos supera el total de la venta.",
                                 parent=self)
            return
        self._pagos.append({
            "medio": medio,
            "importe": importe,
            "comprobante": self.var_comprobante.get().strip() or None,
        })
        self.var_importe.set("")
        self.var_comprobante.set("")
        self._actualizar_tree_pagos()
        self._actualizar_falta()
        self._actualizar_estado_confirmar()

    def _actualizar_tree_pagos(self):
        for i in self.tree_pagos.get_children():
            self.tree_pagos.delete(i)
        for pg in self._pagos:
            self.tree_pagos.insert("", "end", values=(
                pg["medio"], money(pg["importe"]),
                pg["comprobante"] or ""))

    def _quitar_pago(self):
        sel = self.tree_pagos.selection()
        if not sel:
            return
        idx = self.tree_pagos.index(sel[0])
        self._pagos.pop(idx)
        self._actualizar_tree_pagos()
        self._actualizar_falta()
        self._actualizar_estado_confirmar()

    def _precargar_total(self):
        if not self._items:
            messagebox.showwarning("Vacío", "Agregá al menos un producto.",
                                   parent=self)
            return
        self.var_importe.set(money(self._total).replace("$", ""))
        self._actualizar_falta()

    def _cancelar_todo(self):
        self._items = []
        self._pagos = []
        self.var_nombre.set("")
        self.var_apellido.set("")
        self.var_cantidad.set("1")
        self.var_precio.set("")
        self.var_importe.set("")
        self.var_comprobante.set("")
        self._actualizar_items()
        self._actualizar_tree_pagos()
        self._actualizar_falta()
        self.lbl_cliente_ok.config(text="", fg="#9B1C1C")
        self._nombre = ""
        self._apellido = ""

    def _actualizar_estado_confirmar(self):
        listo = (bool(self._nombre) and bool(self._apellido)
                 and bool(self._items)
                 and len(self._pagos) > 0
                 and abs(sum(p["importe"] for p in self._pagos)
                         - self._total) < 0.001)
        self.btn_confirmar.config(state="normal" if listo else "disabled")

    def _confirmar(self):
        if not self._nombre or not self._apellido:
            messagebox.showerror("Cliente", "Completá nombre y apellido.",
                                 parent=self)
            return
        if not self._items:
            messagebox.showerror("Vacío", "Agregá al menos un producto.",
                                 parent=self)
            return
        pagado = sum(p["importe"] for p in self._pagos)
        if abs(pagado - self._total) > 0.001:
            messagebox.showerror("Pagos incompletos",
                                 f"La suma de pagos ({money(pagado)}) no "
                                 f"coincide con el total ({money(self._total)}).",
                                 parent=self)
            return
        caja = db.get_caja(db.hoy())
        if not caja or not db.caja_esta_abierta(caja["id"]):
            messagebox.showerror("Caja cerrada",
                                 "La caja de hoy no está abierta. "
                                 "Abrí la caja antes de registrar ventas.",
                                 parent=self)
            return
        if not db.puede("ventas"):
            messagebox.showerror("Sin permiso",
                                 "No tenés permiso para registrar ventas.",
                                 parent=self)
            return

        token = str(uuid.uuid4())
        cliente_texto = f"{self._nombre} {self._apellido}"

        try:
            ticket = db.registrar_ticket(
                caja["id"], self._items, self._pagos,
                cliente=cliente_texto,
                modulo="USUARIO",
                token_venta=token,
            )
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        db.log_auditoria(
            "Venta confirmada (USUARIO)",
            entidad=f"venta #{ticket['id']}",
            valor_nuevo=f"{cliente_texto} — {money(ticket['total'])}",
            modulo="USUARIO",
            resultado="OK",
        )

        messagebox.showinfo(
            "Venta confirmada",
            f"Venta #{ticket['id']} registrada en MÓDULO USUARIO.\n"
            f"Cliente: {cliente_texto}\n"
            f"Total: {money(ticket['total'])}\n"
            f"Pagos: {db.texto_pagos(ticket['pagos'])}",
            parent=self)
        self._cancelar_todo()
        self.lbl_msg.config(text="Venta registrada correctamente.",
                            fg="#2E7D32")

    def refresh(self):
        self._cargar_productos()
        self._actualizar_items()
        self._actualizar_tree_pagos()
        self._actualizar_falta()
        caja = db.get_caja(db.hoy())
        if caja and db.caja_esta_abierta(caja["id"]):
            self.lbl_bloqueada.config(text="")
        else:
            self.lbl_bloqueada.config(
                text="⚠ La caja de hoy no está abierta. "
                     "Abrila desde Inicio antes de vender.")
