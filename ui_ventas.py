# -*- coding: utf-8 -*-
"""Panel de registro de ventas."""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import estilos as st
from util import money, parse_entero, parse_numero, fecha_larga


class VentasPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._productos = []
        self._construir()

    def _construir(self):
        # Contenido con scroll: nada queda cortado en pantallas chicas
        contenido = st.contenido_scrollable(self)

        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(cab, text="REGISTRO DE VENTAS", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        self.lbl_sub = tk.Label(cab, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                font=(st.FUENTE, 11), wraplength=760,
                                justify="left")
        self.lbl_sub.pack(anchor="w")

        self.lbl_bloqueada = tk.Label(contenido, text="", bg=st.ROJO_CLARO, fg=st.ROJO,
                                      font=(st.FUENTE, 10, "bold"), padx=12, pady=7,
                                      anchor="w")

        # ---------------- Formulario ----------------
        form = st.labelframe(contenido, " NUEVA VENTA ", padx=14, pady=12)
        form.pack(fill="x", padx=24, pady=(14, 0))

        # Dos filas de 4 campos: en pantallas chicas nada queda cortado
        grid = tk.Frame(form, bg=st.FONDO)
        grid.pack(fill="x")
        for c in range(4):
            grid.columnconfigure(c, weight=1)
        for f in range(2):
            grid.rowconfigure(f, weight=1, pad=8)

        def campo(col, etiqueta, fila=0):
            celda = tk.Frame(grid, bg=st.FONDO)
            celda.grid(row=fila, column=col, sticky="nsew", padx=(0, 12))
            lbl = tk.Label(celda, text=etiqueta, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                           font=(st.FUENTE, 9, "bold"))
            lbl.pack(anchor="w")
            return celda, lbl

        c_producto, _ = campo(0, "PRODUCTO", 0)
        self.combo_producto = ttk.Combobox(c_producto, state="readonly", width=22,
                                            font=(st.FUENTE, 11))
        self.combo_producto.pack(fill="x", pady=(3, 0), ipady=3)
        self.combo_producto.bind("<<ComboboxSelected>>", self._producto_cambiado)

        c_cantidad, _ = campo(1, "CANTIDAD", 0)
        self.var_cantidad = tk.StringVar(value="1")
        self.spin_cantidad = ttk.Spinbox(c_cantidad, from_=1, to=9999, width=8,
                                         textvariable=self.var_cantidad,
                                         font=(st.FUENTE, 11), justify="center",
                                         command=self._recalcular)
        self.spin_cantidad.pack(fill="x", pady=(3, 0), ipady=3)
        self.var_cantidad.trace_add("write", lambda *_: self._recalcular())

        c_precio, _ = campo(2, "PRECIO UNITARIO", 0)
        self.var_precio = tk.StringVar(value="")
        self.ent_precio = tk.Entry(c_precio, textvariable=self.var_precio,
                                   font=(st.FUENTE, 11), justify="left",
                                   relief="solid", bd=1)
        self.ent_precio.pack(fill="x", pady=(3, 0), ipady=4)
        self.var_precio.trace_add("write", lambda *_: self._recalcular())

        # Nombre de la persona / cliente (aparece en el Excel exportado)
        c_cliente, _ = campo(3, "NOMBRE / CLIENTE (opcional)", 0)
        self.var_cliente = tk.StringVar(value="")
        self.ent_cliente = tk.Entry(c_cliente, textvariable=self.var_cliente,
                                    font=(st.FUENTE, 11), justify="left",
                                    relief="solid", bd=1)
        self.ent_cliente.pack(fill="x", pady=(3, 0), ipady=4)

        c_medio, _ = campo(0, "MEDIO DE PAGO", 1)
        self.combo_medio = ttk.Combobox(c_medio, state="readonly", width=18,
                                        values=db.MEDIOS_PAGO,
                                        font=(st.FUENTE, 11))
        self.combo_medio.set(db.MEDIOS_PAGO[0])
        self.combo_medio.pack(fill="x", pady=(3, 0), ipady=3)
        self.combo_medio.bind("<<ComboboxSelected>>", self._medio_cambiado)

        # N° de comprobante: obligatorio para Transferencia
        c_comprobante, self.lbl_comprobante = campo(1, "N° DE COMPROBANTE", 1)
        self.var_comprobante = tk.StringVar(value="")
        self.ent_comprobante = tk.Entry(c_comprobante, textvariable=self.var_comprobante,
                                        font=(st.FUENTE, 11), justify="left",
                                        relief="solid", bd=1)
        self.ent_comprobante.pack(fill="x", pady=(3, 0), ipady=4)

        c_total, _ = campo(2, "TOTAL", 1)
        self.lbl_total = tk.Label(c_total, text="$0", bg=st.TARJETA, fg=st.VERDE_OSCURO,
                                  font=(st.FUENTE, 15, "bold"), relief="solid", bd=1,
                                  anchor="e", padx=10)
        self.lbl_total.pack(fill="x", pady=(3, 0), ipady=4)

        celda_btn = tk.Frame(grid, bg=st.FONDO)
        celda_btn.grid(row=1, column=3, sticky="nsew")
        tk.Label(celda_btn, text="", bg=st.FONDO).pack()
        self.btn_registrar = tk.Button(
            celda_btn, text="REGISTRAR VENTA", command=self._registrar,
            relief="flat", bg=st.VERDE, fg="#ffffff", font=(st.FUENTE, 11, "bold"),
            padx=18, pady=9, cursor="hand2",
        )
        self.btn_registrar.pack(fill="x", pady=(3, 0))
        self.btn_registrar.bind("<Enter>",
                                lambda e: self.btn_registrar.config(bg=st.VERDE_OSCURO))
        self.btn_registrar.bind("<Leave>",
                                lambda e: self.btn_registrar.config(bg=st.VERDE))

        self.lbl_info = tk.Label(form, text="", bg=st.FONDO, fg=st.TEXTO,
                                 font=(st.FUENTE, 11, "bold"), anchor="w")
        self.lbl_info.pack(fill="x", pady=(12, 0))

        # ---------------- Listado ----------------
        marco_lista = st.labelframe(contenido, " VENTAS REGISTRADAS ", padx=10, pady=10)
        marco_lista.pack(fill="both", expand=True, padx=24, pady=(14, 24))

        columnas = ("hora", "producto", "cantidad", "precio", "cliente",
                    "medio", "comprobante", "total", "cajero")
        self.tree = ttk.Treeview(marco_lista, columns=columnas, show="headings",
                                 height=12, selectmode="browse")
        self.tree.heading("hora", text="Hora")
        self.tree.heading("producto", text="Producto")
        self.tree.heading("cantidad", text="Cant.")
        self.tree.heading("precio", text="Precio unitario")
        self.tree.heading("cliente", text="Nombre / Cliente")
        self.tree.heading("medio", text="Medio de pago")
        self.tree.heading("comprobante", text="N° Comprobante")
        self.tree.heading("total", text="Total")
        self.tree.heading("cajero", text="Registró")

        self.tree.column("hora", width=62, anchor="center", stretch=False)
        self.tree.column("producto", width=150, anchor="w")
        self.tree.column("cantidad", width=55, anchor="center", stretch=False)
        self.tree.column("precio", width=105, anchor="e")
        self.tree.column("cliente", width=110, anchor="w")
        self.tree.column("medio", width=115, anchor="w")
        self.tree.column("comprobante", width=115, anchor="w")
        self.tree.column("total", width=105, anchor="e")
        self.tree.column("cajero", width=85, anchor="w")

        scroll = ttk.Scrollbar(marco_lista, orient="vertical",
                               command=self.tree.yview)
        scroll_h = ttk.Scrollbar(marco_lista, orient="horizontal",
                                 command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set,
                            xscrollcommand=scroll_h.set)
        # Los bars se ubican primero: el listado ocupa el resto
        scroll.pack(side="right", fill="y")
        scroll_h.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        pie = tk.Frame(contenido, bg=st.FONDO)
        pie.pack(fill="x", padx=24, pady=(0, 20))

        self.btn_editar = tk.Button(
            pie, text="Editar venta seleccionada", command=self._editar,
            relief="flat", bg=st.ACENTO, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=14, pady=8, cursor="hand2",
        )
        self.btn_editar.pack(side="left")
        self.btn_editar.bind("<Enter>",
                             lambda e: self.btn_editar.config(bg=st.ACENTO_OSCURO))
        self.btn_editar.bind("<Leave>",
                             lambda e: self.btn_editar.config(bg=st.ACENTO))

        self.btn_eliminar = tk.Button(
            pie, text="Eliminar venta seleccionada", command=self._eliminar,
            relief="flat", bg=st.ROJO, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=14, pady=8, cursor="hand2",
        )
        self.btn_eliminar.pack(side="left", padx=(10, 0))
        self.btn_eliminar.bind("<Enter>",
                               lambda e: self.btn_eliminar.config(bg="#b91c1c"))
        self.btn_eliminar.bind("<Leave>",
                               lambda e: self.btn_eliminar.config(bg=st.ROJO))

        self.btn_cancelar = tk.Button(
            pie, text="Cancelar edición", command=self._cancelar_edicion,
            relief="flat", bg="#e5eaf1", fg=st.TEXTO, font=(st.FUENTE, 10),
            padx=14, pady=8, cursor="hand2",
        )

        self.lbl_pie = tk.Label(pie, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                font=(st.FUENTE, 10), wraplength=420,
                                justify="right", anchor="e")
        self.lbl_pie.pack(side="right")

        self.lbl_ayuda = tk.Label(
            contenido,
            text="¿Cargaste de más? Seleccioná la venta en la lista y usá "
                 "Editar (corrige sin borrar) o Eliminar.",
            bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9),
            wraplength=760, anchor="w", justify="left",
        )
        self.lbl_ayuda.pack(fill="x", padx=24, pady=(0, 20))

        self._editando_id = None

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
            self.var_precio.set(money(p["precio"]).replace("$", ""))
            self._recalcular()

    def _medio_cambiado(self, _=None):
        """Actualiza el aviso del N° de comprobante según el medio de pago."""
        es_transferencia = self.combo_medio.get() == "Transferencia"
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

    def _medios_permitidos(self):
        """Medios de pago que el usuario puede registrar."""
        return [m for m in db.MEDIOS_PAGO if db.puede(db.MEDIO_PERMISO[m])]

    def _datos_form(self):
        idx = self.combo_producto.current()
        if idx < 0 or idx >= len(self._productos):
            return None
        producto = self._productos[idx]
        cantidad = parse_entero(self.var_cantidad.get())
        precio = parse_numero(self.var_precio.get())
        medio = self.combo_medio.get()
        comprobante = self.var_comprobante.get().strip()
        cliente = self.var_cliente.get().strip()
        if not producto:
            messagebox.showwarning("Venta", "Seleccioná un producto.", parent=self)
            return None
        if not cantidad or cantidad <= 0:
            messagebox.showwarning("Venta", "Ingresá una cantidad válida.",
                                   parent=self)
            return None
        if precio is None or precio <= 0:
            messagebox.showwarning("Venta", "Ingresá un precio unitario válido.",
                                   parent=self)
            return None
        if medio not in db.MEDIOS_PAGO:
            messagebox.showwarning("Venta", "Seleccioná el medio de pago.",
                                   parent=self)
            return None
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
        # Regla: toda transferencia necesita número de comprobante
        if medio == "Transferencia" and not comprobante:
            messagebox.showerror(
                "Falta el comprobante",
                "Para registrar una venta paga con TRANSFERENCIA es obligatorio "
                "ingresar el N° de comprobante.\n\n"
                "Ingresá el número y volvé a presionar "
                "«REGISTRAR VENTA».",
                parent=self,
            )
            self.ent_comprobante.focus_set()
            return None
        return producto, cantidad, precio, medio, comprobante, cliente

    def _recalcular(self, *_):
        cantidad = parse_entero(self.var_cantidad.get()) or 0
        precio = parse_numero(self.var_precio.get()) or 0
        self.lbl_total.config(text=money(cantidad * precio))

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

        linea = f"{cantidad} × {producto['nombre']}\nPrecio unitario: {money(precio)}"
        if medio == "Transferencia":
            linea += f"\nComprobante N°: {comprobante}"
        if cliente:
            linea += f"\nCliente: {cliente}"

        if self._editando_id is not None:
            total = db.actualizar_venta(self._editando_id, producto["id"],
                                        cantidad, precio, medio, comprobante,
                                        cliente)
            numero = self._editando_id
            self._limpiar_edicion()
            messagebox.showinfo("Venta corregida",
                                f"Venta #{numero} actualizada:\n{linea}\n"
                                f"Total: {money(total)}",
                                parent=self)
        else:
            total = db.registrar_venta(caja["id"], producto["id"], cantidad,
                                        precio, medio, comprobante, cliente)
            messagebox.showinfo("Venta registrada",
                                f"{linea}\nTotal: {money(total)}",
                                parent=self)
            self.var_cantidad.set("1")
            self.var_comprobante.set("")
            self.var_cliente.set("")

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

        # Selecciona el producto de la venta en el formulario
        for i, p in enumerate(self._productos):
            if p["id"] == venta["producto_id"]:
                self.combo_producto.current(i)
                break
        self.var_cantidad.set(str(venta["cantidad"]))
        self.var_precio.set(money(venta["precio_unitario"]).replace("$", ""))
        self.combo_medio.set(venta["medio"])
        self.var_comprobante.set(venta.get("comprobante") or "")
        self.var_cliente.set(venta.get("cliente") or "")
        self._medio_cambiado()
        self._editando_id = venta["id"]
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

    def _limpiar_edicion(self):
        self._editando_id = None
        self.btn_registrar.config(text="REGISTRAR VENTA", bg=st.VERDE)
        self.lbl_info.config(fg=st.TEXTO)
        self.btn_cancelar.pack_forget()
        self.var_cantidad.set("1")
        self.var_comprobante.set("")

    def _eliminar(self):
        if self._sin_permiso_ventas():
            return
        caja = self.app.caja_actual()
        if not caja or caja["estado"] != "abierta":
            messagebox.showerror("Caja cerrada",
                                 "No se pueden eliminar ventas de una caja cerrada.",
                                 parent=self)
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Eliminar", "Seleccioná una venta de la lista.",
                                   parent=self)
            return
        venta_id = int(sel[0])
        if not messagebox.askyesno("Eliminar venta",
                                   "¿Eliminar la venta seleccionada?", parent=self):
            return
        db.eliminar_venta(venta_id)
        if self._editando_id == venta_id:
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
            self.lbl_bloqueada.pack(fill="x", padx=24, pady=(10, 0))
            if sin_abrir:
                self.lbl_bloqueada.config(
                    text="■ CAJA SIN ABRIR: presioná ABRIR CAJA en la pantalla "
                         "Inicio para registrar el monto inicial y poder "
                         "cargar ventas."
                )
            else:
                self.lbl_bloqueada.config(
                    text="■ CAJA CERRADA: no se pueden registrar ni eliminar ventas. "
                         "Para modificar, usá la reapertura de caja en Historial."
                )

        # Estado de los controles
        self.combo_producto.configure(state="readonly" if operativa else "disabled")
        self.spin_cantidad.configure(state="normal" if operativa else "disabled")
        self.ent_precio.configure(state="normal" if operativa else "disabled")
        self.ent_cliente.configure(state="normal" if operativa else "disabled")
        self.combo_medio.configure(state="readonly" if operativa else "disabled")
        self.ent_comprobante.configure(state="normal" if operativa else "disabled")
        self.btn_registrar.config(state="normal" if operativa else "disabled",
                                  bg=st.VERDE if operativa else "#a3d9b5")
        self.btn_eliminar.config(state="normal" if operativa else "disabled",
                                 bg=st.ROJO if operativa else "#f0a8a8")

        # Solo se ofrecen los medios de pago que el usuario puede registrar
        medios = self._medios_permitidos()
        self.combo_medio["values"] = medios
        if operativa and medios and self.combo_medio.get() not in medios:
            self.combo_medio.set(medios[0])
            self._medio_cambiado()

        # Productos
        self._productos = db.productos()
        nombres = [p["nombre"] for p in self._productos]
        seleccion_previa = self.combo_producto.get()
        self.combo_producto["values"] = nombres
        if seleccion_previa in nombres:
            self.combo_producto.set(seleccion_previa)
        elif nombres:
            self.combo_producto.current(0)
            self._producto_cambiado()

        # Listado de ventas
        self.tree.delete(*self.tree.get_children())
        r = db.resumen(caja["id"])
        for v in r["ventas"]:
            hora = v["fecha_hora"].split(" ")[1][:5] if v["fecha_hora"] else ""
            self.tree.insert(
                "", "end", iid=str(v["id"]),
                tags=("cerrada",) if not operativa else (),
                values=(
                    hora,
                    v["producto"] or "—",
                    v["cantidad"],
                    money(v["precio_unitario"]),
                    v.get("cliente") or "—",
                    v["medio"],
                    v.get("comprobante") or ("—" if v["medio"] != "Transferencia" else ""),
                    money(v["total"]),
                    v.get("cajero") or "—",
                ),
            )
        if not operativa:
            self.tree.tag_configure("cerrada", foreground=st.TEXTO_SUAVE)

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
