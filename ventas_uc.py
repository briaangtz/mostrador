"""
ventas_uc.py  -  Pantalla "Ventas U.C" (Usuario / Comercio) - Tkinter puro

USO (en tu ventana principal, donde ya manejás tus pantallas/Frames):

    from ventas_uc import VentasUCFrame

    self.ventas_uc = VentasUCFrame(self.contenedor, on_confirmar=self.guardar_venta_uc)
    # mostrarlo igual que tus otras pantallas:
    self.ventas_uc.pack(fill="both", expand=True)       # o .grid(...)

    def guardar_venta_uc(self, venta: dict):
        # venta = {
        #   "tipo": "usuario" | "comercio",
        #   "comprador": {"nombre","apellido"}  o  {"comercio","titular"},
        #   "items": [{"producto","precio","cantidad","subtotal"}, ...],
        #   "pagos": [{"medio","importe","comprobante"}, ...],
        #   "total": int, "pagado": int, "saldo": int
        # }
        ...   # <-- acá lo guardás en tu base / caja

Otros métodos:
    ventas_uc.set_estado_caja(True/False)   # bloquea CONFIRMAR si la caja está cerrada
    ventas_uc.limpiar()

Parámetro show_header=True dibuja el "Inicio > Ventas U.C" y el cartel "Abierta"
propios. Por defecto está en False porque tu app ya los muestra en la barra superior.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db

# ----------------------------------------------------------------------
# CONFIGURACIÓN (precios leídos de la tabla de precios por módulo en Configuración)
# ----------------------------------------------------------------------
# precio = None  ->  muestra "[precio]" y queda bloqueado hasta que cargues el valor en Configuración
MEDIOS_SIN_COMPROBANTE = {"Efectivo"}

# ----------------------------------------------------------------------
# ESTILO
# ----------------------------------------------------------------------
FONT = "Segoe UI"
BG = "#f1f5f9"
CARD_BORDER = "#e2e8f0"
INPUT_BORDER = "#cbd5e1"
TXT = "#0f172a"
TXT_MUTED = "#64748b"
TXT_DIM = "#94a3b8"
THEAD_BG = "#eef2f7"
ROW_ACTIVE = "#eff6ff"
BLUE = "#2563eb"
BLUE_HOVER = "#1d4ed8"
BLUE_DISABLED = "#93c5fd"
GREEN = "#15803d"
GREEN_HOVER = "#166534"
RED = "#b91c1c"
DISABLED_BG = "#e8edf3"


def fmt(n):
    """90000 -> $90.000"""
    return "$" + f"{int(n):,}".replace(",", ".")


def parse_importe(texto):
    """'25.000' / '25000' / '$ 25.000' -> 25000"""
    solo = "".join(c for c in str(texto) if c.isdigit())
    return int(solo) if solo else 0


def _hover(btn, normal, over):
    btn.bind("<Enter>", lambda e: btn.config(bg=over) if str(btn["state"]) == "normal" else None)
    btn.bind("<Leave>", lambda e: btn.config(bg=normal) if str(btn["state"]) == "normal" else None)


def _boton(parent, text, bg, hover, command, fg="white", size=10, padx=14, pady=8):
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                  activebackground=hover, activeforeground=fg, relief="flat", bd=0,
                  font=(FONT, size, "bold"), cursor="hand2", padx=padx, pady=pady,
                  highlightthickness=0)
    _hover(b, bg, hover)
    return b


def _entry(parent, textvariable=None, **kw):
    return tk.Entry(parent, textvariable=textvariable, font=(FONT, 11), relief="flat", bd=0,
                    bg="white", fg=TXT, insertbackground=TXT,
                    highlightthickness=1, highlightbackground=INPUT_BORDER,
                    highlightcolor=BLUE, disabledbackground=DISABLED_BG,
                    disabledforeground=TXT_DIM, **kw)


def _config_cols(frame):
    """Mismas columnas para encabezado y filas (así quedan alineadas)."""
    for col, w in enumerate((3, 2, 4, 2)):
        frame.grid_columnconfigure(col, weight=w, uniform="prod")


# ----------------------------------------------------------------------
# FILA DE PRODUCTO
# ----------------------------------------------------------------------
class _FilaProducto:
    def __init__(self, parent, nombre, precio, on_change):
        self.nombre = nombre.replace("\n", " ")
        self.precio = precio
        self.on_change = on_change

        self.frame = tk.Frame(parent, bg="white")
        _config_cols(self.frame)

        self.var = tk.StringVar(value="0")
        self.var.trace_add("write", lambda *a: self._cambio())

        self.lbl_nombre = tk.Label(self.frame, text=nombre, anchor="w", justify="left",
                                   bg="white", font=(FONT, 11, "bold"))
        self.lbl_precio = tk.Label(self.frame, anchor="e", bg="white", font=(FONT, 10),
                                   text=fmt(precio) if precio is not None else "[precio]")
        self.cant = tk.Frame(self.frame, bg="white")
        self.lbl_sub = tk.Label(self.frame, text="$0", anchor="e", bg="white",
                                font=(FONT, 11, "bold"))

        self.lbl_nombre.grid(row=0, column=0, sticky="w", padx=(12, 0), pady=8)
        self.lbl_precio.grid(row=0, column=1, sticky="e", padx=(0, 6))
        self.cant.grid(row=0, column=2)
        self.lbl_sub.grid(row=0, column=3, sticky="e", padx=(0, 12))

        self.btn_minus = tk.Button(self.cant, text="−", width=2, command=lambda: self._sumar(-1),
                                   bg="white", fg="#0284c7", activebackground="#f1f5f9",
                                   relief="flat", bd=0, font=(FONT, 13, "bold"), cursor="hand2",
                                   highlightthickness=1, highlightbackground=INPUT_BORDER)
        vcmd = (self.frame.register(lambda P: P == "" or (P.isdigit() and len(P) <= 4)), "%P")
        self.entry = tk.Entry(self.cant, textvariable=self.var, width=4, justify="center",
                              font=(FONT, 13, "bold"), relief="flat", bd=0, bg="white", fg=TXT,
                              highlightthickness=1, highlightbackground=INPUT_BORDER,
                              highlightcolor=BLUE, validate="key", validatecommand=vcmd,
                              disabledbackground=DISABLED_BG, disabledforeground=TXT_DIM)
        self.btn_plus = tk.Button(self.cant, text="+", width=2, command=lambda: self._sumar(1),
                                  bg=BLUE, fg="white", activebackground=BLUE_HOVER,
                                  activeforeground="white", relief="flat", bd=0,
                                  font=(FONT, 13, "bold"), cursor="hand2", highlightthickness=0)
        _hover(self.btn_plus, BLUE, BLUE_HOVER)

        self.btn_minus.pack(side="left", ipady=3)
        self.entry.pack(side="left", padx=8, ipady=6)
        self.btn_plus.pack(side="left", ipady=3)

        if precio is None:                     # sin precio -> bloqueado
            for w in (self.btn_minus, self.btn_plus):
                w.config(state="disabled", bg=DISABLED_BG, cursor="arrow")
            self.entry.config(state="disabled")
        self._refrescar()

    @property
    def cantidad(self):
        try:
            return int(self.var.get() or 0)
        except ValueError:
            return 0

    @property
    def subtotal(self):
        return (self.precio or 0) * self.cantidad

    def _sumar(self, d):
        self.var.set(str(max(0, self.cantidad + d)))

    def reset(self):
        self.var.set("0")

    def _cambio(self):
        self._refrescar()
        self.on_change()

    def _refrescar(self):
        activo = self.cantidad > 0
        bg = ROW_ACTIVE if activo else "white"
        fg = TXT if activo else TXT_DIM
        for w in (self.frame, self.cant, self.lbl_nombre, self.lbl_precio, self.lbl_sub):
            w.config(bg=bg)
        self.lbl_nombre.config(fg=fg, font=(FONT, 11, "bold"))
        self.lbl_precio.config(fg=fg)
        self.lbl_sub.config(fg=fg, text=fmt(self.subtotal))


# ----------------------------------------------------------------------
# PANTALLA PRINCIPAL
# ----------------------------------------------------------------------
class VentasUCFrame(tk.Frame):
    def __init__(self, parent, on_confirmar=None, show_header=False, caja_abierta=True):
        super().__init__(parent, bg=BG)
        self.on_confirmar = on_confirmar
        self.show_header = show_header
        self.caja_abierta = caja_abierta
        self.tipo = "usuario"
        self.pagos = []
        self.productos = []          # lista de dicts de db.productos()
        self._build()
        self._cargar_productos_del_tipo()
        self._recalcular()

    # ---------------- helpers de UI ----------------
    def _card(self, parent):
        return tk.Frame(parent, bg="white", highlightbackground=CARD_BORDER, highlightthickness=1)

    def _build(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=26, pady=16)

        # --- cabecera opcional
        if self.show_header:
            top = tk.Frame(outer, bg=BG)
            top.pack(fill="x")
            tk.Label(top, text="Inicio  >  Ventas U.C", bg=BG, fg=TXT_MUTED,
                     font=(FONT, 9)).pack(side="left")
            self.badge = tk.Label(top, text="Abierta", bg="#dcfce7", fg=GREEN,
                                  font=(FONT, 9, "bold"), padx=12, pady=3)
            self.badge.pack(side="right")

        # --- título + toggle
        head = tk.Frame(outer, bg=BG)
        head.pack(fill="x", pady=(8, 12))
        tk.Label(head, text="Ventas U.C", bg=BG, fg=TXT, font=(FONT, 24, "bold")).pack(side="left")
        tk.Label(head, text="Usuario / Comercio", bg=BG, fg=TXT_MUTED,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(8, 0), pady=(10, 0))

        box = tk.Frame(head, bg="#e2e8f0", padx=4, pady=4)
        box.pack(side="right")
        self.btn_user = tk.Button(box, text="USUARIO", relief="flat", bd=0, cursor="hand2",
                                  font=(FONT, 10, "bold"), padx=20, pady=7,
                                  command=lambda: self._set_tipo("usuario"))
        self.btn_com = tk.Button(box, text="COMERCIO", relief="flat", bd=0, cursor="hand2",
                                 font=(FONT, 10, "bold"), padx=20, pady=7,
                                 command=lambda: self._set_tipo("comercio"))
        self.btn_user.pack(side="left")
        self.btn_com.pack(side="left")

        # --- cuerpo: 2 columnas
        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=5, uniform="cols")
        body.grid_columnconfigure(1, weight=4, uniform="cols")
        body.grid_rowconfigure(0, weight=1)

        izq = tk.Frame(body, bg=BG)
        der = tk.Frame(body, bg=BG)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        der.grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        self._card_comprador(izq)
        self._card_productos(izq)
        self._card_pagos(der)
        self._card_total(der)
        self._btn_confirmar(der)

        self._set_tipo("usuario")

    # ---------------- comprador ----------------
    def _card_comprador(self, parent):
        c = self._card(parent)
        c.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(c, bg="white")
        inner.pack(fill="x", padx=18, pady=(14, 16))

        self.lbl_comprador = tk.Label(inner, text="Comprador (Usuario)", bg="white", fg=TXT,
                                      font=(FONT, 15, "bold"), anchor="w")
        self.lbl_comprador.pack(fill="x", pady=(0, 8))

        fila = tk.Frame(inner, bg="white")
        fila.pack(fill="x")
        fila.grid_columnconfigure(0, weight=1, uniform="f")
        fila.grid_columnconfigure(1, weight=1, uniform="f")

        self.lbl_f1 = tk.Label(fila, text="NOMBRE", bg="white", fg="#475569",
                               font=(FONT, 8, "bold"), anchor="w")
        self.lbl_f2 = tk.Label(fila, text="APELLIDO", bg="white", fg="#475569",
                               font=(FONT, 8, "bold"), anchor="w")
        self.ed_nombre = _entry(fila)
        self.ed_apellido = _entry(fila)
        self.lbl_f1.grid(row=0, column=0, sticky="w")
        self.lbl_f2.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.ed_nombre.grid(row=1, column=0, sticky="ew", ipady=7, pady=(3, 0))
        self.ed_apellido.grid(row=1, column=1, sticky="ew", ipady=7, pady=(3, 0), padx=(12, 0))

    # ---------------- productos ----------------
    def _card_productos(self, parent):
        c = self._card(parent)
        c.pack(fill="both", expand=True)
        inner = tk.Frame(c, bg="white")
        inner.pack(fill="both", expand=True, padx=18, pady=(14, 12))

        tk.Label(inner, text="Productos", bg="white", fg=TXT, font=(FONT, 15, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 8))

        # contenedor de filas (se reconstruye al cambiar de tipo)
        self.filas_container = tk.Frame(inner, bg="white")
        self.filas_container.pack(fill="both", expand=True)

        # total
        tot = tk.Frame(inner, bg="white")
        tot.pack(fill="x", pady=(10, 0))
        self.lbl_total_prod = tk.Label(tot, text="$0", bg="white", fg=TXT,
                                       font=(FONT, 22, "bold"))
        self.lbl_total_prod.pack(side="right")
        tk.Label(tot, text="TOTAL", bg="white", fg="#334155",
                 font=(FONT, 10, "bold")).pack(side="right", padx=(0, 10), pady=(8, 0))

        tk.Label(inner, text="Los envases no van acá: se venden en su propia sección.",
                 bg="white", fg=TXT_MUTED, font=(FONT, 8), anchor="e").pack(fill="x")

    def _reconstruir_filas_productos(self):
        """Crea las filas de producto desde DB según el tipo actual (usuario/comercio)."""
        for w in self.filas_container.winfo_children():
            w.destroy()

        # encabezado (mismas columnas que las filas)
        th = tk.Frame(self.filas_container, bg=THEAD_BG)
        th.pack(fill="x")
        _config_cols(th)
        for col, (txt, anchor, padx) in enumerate([("PRODUCTO", "w", (12, 0)),
                                                   ("PRECIO", "e", (0, 6)),
                                                   ("CANTIDAD", "center", (0, 0)),
                                                   ("SUBTOTAL", "e", (0, 12))]):
            tk.Label(th, text=txt, bg=THEAD_BG, fg="#475569", font=(FONT, 8, "bold"),
                     anchor=anchor).grid(row=0, column=col, sticky="ew", padx=padx, pady=7)

        # filas de productos desde DB
        self.filas = []
        tipo_modulo = "USUARIO" if self.tipo == "usuario" else "COMERCIO"
        precios = db.get_precios_usuario() if self.tipo == "usuario" else db.get_precios_comercio()

        for p in self.productos:
            pid = p["id"]
            nombre = p["nombre"]
            precio_centavos = precios.get(pid)
            precio = precio_centavos / 100.0 if precio_centavos is not None else None
            f = _FilaProducto(self.filas_container, nombre, precio, self._recalcular)
            f.frame.pack(fill="x")
            tk.Frame(self.filas_container, bg=CARD_BORDER, height=1).pack(fill="x")
            self.filas.append(f)

    # ---------------- medios de pago ----------------
    def _card_pagos(self, parent):
        c = self._card(parent)
        c.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(c, bg="white")
        inner.pack(fill="x", padx=18, pady=(14, 16))

        tk.Label(inner, text="Medios de pago", bg="white", fg=TXT, font=(FONT, 12, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 8))

        th = tk.Frame(inner, bg=THEAD_BG)
        th.pack(fill="x")
        for col in range(3):
            th.grid_columnconfigure(col, weight=1, uniform="pg")
        for col, txt in enumerate(["Medio", "Importe", "Comprobante"]):
            tk.Label(th, text=txt, bg=THEAD_BG, fg="#475569",
                     font=(FONT, 9, "bold")).grid(row=0, column=col, sticky="ew", pady=6)

        # lista de pagos agregados
        self.lista_pagos = tk.Frame(inner, bg="white", height=60)
        self.lista_pagos.pack(fill="x", pady=(4, 8))

        # fila de carga
        fila = tk.Frame(inner, bg="white")
        fila.pack(fill="x")
        for col in range(3):
            fila.grid_columnconfigure(col, weight=1, uniform="ld")

        self.var_medio = tk.StringVar(value=db.MEDIOS_PAGO[0])
        self.cb_medio = ttk.Combobox(fila, textvariable=self.var_medio, values=db.MEDIOS_PAGO,
                                     state="readonly", font=(FONT, 10))
        self.cb_medio.bind("<<ComboboxSelected>>", lambda e: self._medio_cambio())
        self.ed_importe = _entry(fila)
        self.ed_importe.bind("<Return>", lambda e: self._agregar_pago())
        self.ed_comprobante = _entry(fila)

        self.cb_medio.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 6))
        self.ed_importe.grid(row=0, column=1, sticky="ew", ipady=7, padx=3)
        self.ed_comprobante.grid(row=0, column=2, sticky="ew", ipady=7, padx=(6, 0))
        self._medio_cambio()

        btns = tk.Frame(inner, bg="white")
        btns.pack(fill="x", pady=(10, 0))
        _boton(btns, "+ AGREGAR PAGO", BLUE, BLUE_HOVER, self._agregar_pago,
               size=9).pack(side="left")
        _boton(btns, "Pagar saldo restante", GREEN, GREEN_HOVER, self._pagar_saldo,
               size=9).pack(side="left", padx=(8, 0))

    # ---------------- totales ----------------
    def _card_total(self, parent):
        c = self._card(parent)
        c.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(c, bg="white")
        inner.pack(fill="x", padx=18, pady=14)

        self.lbl_total = tk.Label(inner, text="Total: $0", bg="white", fg=TXT,
                                  font=(FONT, 16, "bold"))
        self.lbl_total.pack()
        fila = tk.Frame(inner, bg="white")
        fila.pack(pady=(4, 0))
        self.lbl_pagado = tk.Label(fila, text="Pagado: $0", bg="white", fg=GREEN, font=(FONT, 10))
        self.lbl_saldo = tk.Label(fila, text="Saldo: $0", bg="white", fg=RED, font=(FONT, 10))
        self.lbl_pagado.pack(side="left", padx=(0, 22))
        self.lbl_saldo.pack(side="left")
        self.lbl_aviso = tk.Label(inner, text="", bg="white", fg=RED, font=(FONT, 9, "bold"))
        self.lbl_aviso.pack(pady=(6, 0))

    def _btn_confirmar(self, parent):
        self.btn_confirmar = tk.Button(
            parent, text="CONFIRMAR VENTA", command=self._confirmar, relief="flat", bd=0,
            font=(FONT, 12, "bold"), fg="white", bg=BLUE, activebackground=BLUE_HOVER,
            activeforeground="white", cursor="hand2", pady=13, highlightthickness=0,
            disabledforeground="white")
        self.btn_confirmar.pack(fill="x")
        _hover(self.btn_confirmar, BLUE, BLUE_HOVER)

    # ---------------- lógica ----------------
    def _set_tipo(self, tipo):
        self.tipo = tipo
        on = dict(bg=BLUE, fg="white", activebackground=BLUE_HOVER, activeforeground="white")
        off = dict(bg="#e2e8f0", fg="#334155", activebackground="#cbd5e1", activeforeground="#334155")
        self.btn_user.config(**(on if tipo == "usuario" else off))
        self.btn_com.config(**(on if tipo == "comercio" else off))

        # Usuario: Nombre / Apellido.  Comercio: Nombre del comercio / Titular
        # (cambiá los textos si en tu sistema son otros campos)
        if tipo == "usuario":
            self.lbl_comprador.config(text="Comprador (Usuario)")
            self.lbl_f1.config(text="NOMBRE")
            self.lbl_f2.config(text="APELLIDO")
        else:
            self.lbl_comprador.config(text="Comprador (Comercio)")
            self.lbl_f1.config(text="NOMBRE DEL COMERCIO")
            self.lbl_f2.config(text="TITULAR / RESPONSABLE")

        # Recargar productos y precios desde DB según el módulo
        self._cargar_productos_del_tipo()

    def _cargar_productos_del_tipo(self):
        """Carga los productos activos de DB y reconstruye las filas con
        el precio del módulo actual (USUARIO o COMERCIO)."""
        self.productos = db.productos(solo_activos=True)
        self._reconstruir_filas_productos()
        self._recalcular()

    def _medio_cambio(self):
        sin = self.var_medio.get() in MEDIOS_SIN_COMPROBANTE
        if sin:
            self.ed_comprobante.config(state="normal")
            self.ed_comprobante.delete(0, "end")
        self.ed_comprobante.config(state="disabled" if sin else "normal")

    def _total(self):
        return sum(f.subtotal for f in self.filas)

    def _pagado(self):
        return sum(p["importe"] for p in self.pagos)

    def _recalcular(self):
        total, pagado = self._total(), self._pagado()
        saldo = total - pagado
        self.lbl_total_prod.config(text=fmt(total))
        self.lbl_total.config(text=f"Total: {fmt(total)}")
        self.lbl_pagado.config(text=f"Pagado: {fmt(pagado)}")
        self.lbl_saldo.config(text=f"Saldo: {fmt(saldo)}")

        if not self.caja_abierta:
            aviso = "La caja está cerrada."
        elif total == 0:
            aviso = "Agregá al menos un producto a la venta."
        else:
            aviso = ""
        self.lbl_aviso.config(text=aviso)

        habilitado = self.caja_abierta and total > 0
        if habilitado:
            self.btn_confirmar.config(state="normal", bg=BLUE, cursor="hand2")
        else:
            self.btn_confirmar.config(state="disabled", bg=BLUE_DISABLED, cursor="arrow")

    def _agregar_pago(self):
        importe = parse_importe(self.ed_importe.get())
        if importe <= 0:
            messagebox.showwarning("Pago", "Ingresá un importe mayor a 0.", parent=self)
            return
        self.pagos.append({
            "medio": self.var_medio.get(),
            "importe": importe,
            "comprobante": self.ed_comprobante.get().strip(),
        })
        self.ed_importe.delete(0, "end")
        if str(self.ed_comprobante["state"]) == "normal":
            self.ed_comprobante.delete(0, "end")
        self._dibujar_pagos()

    def _pagar_saldo(self):
        saldo = self._total() - self._pagado()
        if saldo <= 0:
            messagebox.showinfo("Pago", "No hay saldo pendiente.", parent=self)
            return
        self.ed_importe.delete(0, "end")
        self.ed_importe.insert(0, str(saldo))
        self._agregar_pago()

    def _quitar_pago(self, idx):
        if 0 <= idx < len(self.pagos):
            self.pagos.pop(idx)
            self._dibujar_pagos()

    def _dibujar_pagos(self):
        for w in self.lista_pagos.winfo_children():
            w.destroy()
        for i, p in enumerate(self.pagos):
            row = tk.Frame(self.lista_pagos, bg="white")
            row.pack(fill="x", pady=1)
            for col in range(3):
                row.grid_columnconfigure(col, weight=1, uniform="pg")
            for col, txt in enumerate((p["medio"], fmt(p["importe"]), p["comprobante"] or "—")):
                tk.Label(row, text=txt, bg="white", fg=TXT,
                         font=(FONT, 10)).grid(row=0, column=col, sticky="ew")
            tk.Button(row, text="✕", bg="white", fg=RED, activeforeground="#7f1d1d",
                      relief="flat", bd=0, cursor="hand2", font=(FONT, 10, "bold"),
                      command=lambda k=i: self._quitar_pago(k)).grid(row=0, column=3)
        self._recalcular()

    def _confirmar(self):
        if not self.caja_abierta:
            messagebox.showwarning("Venta", "La caja está cerrada.", parent=self)
            return
        items = [{"producto": f.nombre, "precio": f.precio, "cantidad": f.cantidad,
                  "subtotal": f.subtotal} for f in self.filas if f.cantidad > 0]
        if not items:
            messagebox.showwarning("Venta", "Agregá al menos un producto.", parent=self)
            return
        nom = self.ed_nombre.get().strip()
        ape = self.ed_apellido.get().strip()
        if not nom:
            messagebox.showwarning("Venta", "Completá los datos del comprador.", parent=self)
            return

        total, pagado = self._total(), self._pagado()
        saldo = total - pagado
        if saldo > 0:
            if not messagebox.askyesno("Saldo pendiente",
                                       f"Queda un saldo de {fmt(saldo)}.\n¿Confirmar la venta igual?",
                                       parent=self):
                return
        elif saldo < 0:
            messagebox.showwarning("Pago", "Lo pagado supera el total de la venta.", parent=self)
            return

        venta = {
            "tipo": self.tipo,
            "comprador": ({"nombre": nom, "apellido": ape} if self.tipo == "usuario"
                          else {"comercio": nom, "titular": ape}),
            "items": items,
            "pagos": list(self.pagos),
            "total": total, "pagado": pagado, "saldo": saldo,
        }
        if self.on_confirmar:
            self.on_confirmar(venta)
        self.limpiar()

    # ---------------- API pública ----------------
    def limpiar(self):
        self.ed_nombre.delete(0, "end")
        self.ed_apellido.delete(0, "end")
        for f in self.filas:
            f.reset()
        self.pagos.clear()
        self._dibujar_pagos()

    def set_estado_caja(self, abierta):
        self.caja_abierta = bool(abierta)
        if self.show_header:
            self.badge.config(text="Abierta" if abierta else "Cerrada",
                              bg="#dcfce7" if abierta else "#fee2e2",
                              fg=GREEN if abierta else RED)
        self._recalcular()

    def refresh(self):
        """Refresca el panel al mostrarlo."""
        self._recalcular()


# ----------------------------------------------------------------------
# Prueba suelta:  python ventas_uc.py
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Ventas U.C - prueba")
    root.geometry("1080x780")
    VentasUCFrame(root, on_confirmar=print, show_header=True).pack(fill="both", expand=True)
    root.mainloop()
