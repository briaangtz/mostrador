# -*- coding: utf-8 -*-
"""Pantalla de inicio de sesión (obligatoria para usar el sistema)."""

import tkinter as tk

import database as db
import estilos as st
import iconos as ic
from widgets_figma import Btn


class LoginDialog(tk.Toplevel):
    """Ventana modal de usuario + contraseña."""

    def __init__(self, master):
        super().__init__(master)
        self.resultado = None
        FONDO = st.SIDEBAR

        self.title("Iniciar sesión")
        self.configure(bg=FONDO)
        self.resizable(False, False)
        # NOTA: no usar transient(master): la raíz está oculta (withdraw)
        # esperando el login y Windows no dibuja una ventana transient
        # cuyo dueño está oculta. La modalidad la da wait_window + grab.
        self.protocol("WM_DELETE_WINDOW", self._salir)

        ancho, alto = 440, 560
        self.geometry(f"{ancho}x{alto}")
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2 - 40)
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.focus_force()

        cont = tk.Frame(self, bg=FONDO)
        cont.pack(fill="both", expand=True, padx=44, pady=(40, 30))

        # Marca: llama sobre cuadro azul + nombre
        marca = tk.Frame(cont, bg=FONDO)
        marca.pack(anchor="w")
        tk.Label(marca, bg=FONDO, image=ic.cuadro(
            "flame", 54, "#FFFFFF", st.ACENTO, 13, 30, 1.8)
        ).pack(side="left", padx=(0, 14))
        col = tk.Frame(marca, bg=FONDO)
        col.pack(side="left")
        tk.Label(col, text="DOBLE G SRL", bg=FONDO, fg="#ffffff",
                 font=(st.FUENTE, 22)).pack(anchor="w")
        tk.Label(col, text="Control de caja diaria", bg=FONDO, fg="#9fb0cc",
                 font=(st.FUENTE, 10)).pack(anchor="w")

        tk.Label(cont, text="Iniciar sesión", bg=FONDO, fg="#ffffff",
                 font=(st.FUENTE, 16, "bold")).pack(anchor="w", pady=(30, 0))
        tk.Label(cont, text="DOBLE G SRL — ingresá tus datos", bg=FONDO,
                 fg="#9fb0cc", font=(st.FUENTE, 10), anchor="w", justify="left",
                 wraplength=350).pack(fill="x", anchor="w", pady=(2, 20))

        def campo(texto, icono, mostrar=""):
            tk.Label(cont, text=texto, bg=FONDO, fg="#c7d2e4",
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            fila = tk.Frame(cont, bg="#FFFFFF", highlightthickness=1,
                            highlightbackground="#2A4376",
                            highlightcolor=st.ACENTO)
            fila.pack(fill="x", pady=(5, 16))
            tk.Label(fila, bg="#FFFFFF", image=ic.icono(icono, 18, "#64748B", 1.8)
                     ).pack(side="left", padx=(12, 6))
            var = tk.StringVar()
            ent = tk.Entry(fila, textvariable=var, font=(st.FUENTE, 13),
                           relief="flat", bd=0, show=mostrar, bg="#FFFFFF",
                           fg=st.TEXTO, insertbackground=st.TEXTO,
                           highlightthickness=0)
            ent.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))
            return var, ent

        self.var_usuario, self.ent_usuario = campo("USUARIO", "user")
        self.var_password, self.ent_password = campo("CONTRASEÑA", "lock",
                                                     mostrar="•")

        self.lbl_error = tk.Label(cont, text="", bg=FONDO, fg="#fca5a5",
                                  font=(st.FUENTE, 9), anchor="w", justify="left")
        self.lbl_error.pack(fill="x")

        fila = tk.Frame(cont, bg=FONDO)
        fila.pack(fill="x", pady=(18, 0))
        fila.columnconfigure(0, weight=1, uniform="b")
        fila.columnconfigure(1, weight=1, uniform="b")

        btn_salir = Btn(fila, text="SALIR", command=self._salir, bg="#3b4a6b",
                        fg="#ffffff", font=(st.FUENTE, 11, "bold"),
                        padx=18, pady=12)
        btn_salir.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        btn_ingresar = Btn(fila, text="INGRESAR", command=self._ingresar,
                           bg=st.VERDE, fg="#ffffff",
                           font=(st.FUENTE, 11, "bold"), padx=18, pady=12)
        btn_ingresar.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.bind("<Return>", lambda e: self._ingresar())
        self.bind("<Escape>", lambda e: self._salir())
        self.after(50, self._enfocar)

    def _enfocar(self):
        try:
            self.ent_usuario.focus_set()
        except tk.TclError:
            pass          # la ventana ya se cerró

    # ------------------------------------------------------------- acciones
    def _ingresar(self):
        usuario = self.var_usuario.get().strip()
        password = self.var_password.get()
        if not usuario or not password:
            self.lbl_error.config(text="Ingresá el usuario y la contraseña.")
            return
        u = db.iniciar_sesion(usuario, password)
        if not u:
            self.lbl_error.config(
                text="Usuario o contraseña incorrectos,\no el usuario está desactivado.")
            self.var_password.set("")
            self.ent_password.focus_set()
            return
        self.resultado = u
        self.destroy()

    def _salir(self):
        self.resultado = None
        self.destroy()


def cambiar_password_inicial(parent, usuario):
    """Cambio obligatorio de la contraseña de fábrica ('admin').

    Nadie debería seguir con la contraseña que viene de instalación
    (hallazgo AppSec #3). Devuelve True si el usuario creó una nueva
    y False si prefirió salir sin cambiarla."""
    dlg = tk.Toplevel(parent)
    dlg.title("Cambio de contraseña obligatorio")
    FONDO = st.SIDEBAR
    dlg.configure(bg=FONDO)
    dlg.resizable(False, False)
    # Sin transient: la raíz sigue oculta esperando el login (igual que
    # LoginDialog); la modalidad la dan grab_set + wait_window.
    dlg.protocol("WM_DELETE_WINDOW", lambda: _cerrar(False))

    ancho, alto = 430, 360
    dlg.geometry(f"{ancho}x{alto}")
    dlg.update_idletasks()
    x = max(0, (dlg.winfo_screenwidth() - ancho) // 2)
    y = max(0, (dlg.winfo_screenheight() - alto) // 2 - 40)
    dlg.geometry(f"+{x}+{y}")
    dlg.lift()
    dlg.focus_force()

    cont = tk.Frame(dlg, bg=FONDO)
    cont.pack(fill="both", expand=True, padx=36, pady=(34, 28))

    tk.Label(cont, text="Creá tu contraseña nueva", bg=FONDO, fg="#ffffff",
             font=(st.FUENTE, 16, "bold")).pack(anchor="w")
    tk.Label(cont, text=(
        "Ingresaste con la contraseña inicial de instalación. "
        "Para seguir, elegí una propia (mínimo 4 caracteres)."),
        bg=FONDO, fg="#9fb0cc", font=(st.FUENTE, 10), justify="left",
        wraplength=350).pack(anchor="w", pady=(8, 18))

    def campo(texto):
        tk.Label(cont, text=texto, bg=FONDO, fg="#c7d2e4",
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        caja = tk.Frame(cont, bg="#FFFFFF", highlightthickness=1,
                        highlightbackground="#2A4376",
                        highlightcolor=st.ACENTO)
        caja.pack(fill="x", pady=(3, 14))
        var = tk.StringVar()
        tk.Entry(caja, textvariable=var, font=(st.FUENTE, 13),
                 relief="flat", bd=0, show="•", bg="#FFFFFF", fg=st.TEXTO,
                 insertbackground=st.TEXTO, highlightthickness=0
                 ).pack(fill="x", ipady=9, padx=(12, 12))
        return var

    var_nueva = campo("CONTRASEÑA NUEVA")
    var_repetir = campo("REPETÍ LA CONTRASEÑA")

    lbl_error = tk.Label(cont, text="", bg=FONDO, fg="#fca5a5",
                         font=(st.FUENTE, 9), anchor="w", justify="left")
    lbl_error.pack(fill="x")

    def _cerrar(valor):
        dlg.resultado = valor
        dlg.destroy()

    def guardar():
        nueva = var_nueva.get()
        if len(nueva) < 4:
            lbl_error.config(text="La contraseña debe tener al menos 4 caracteres.")
            return
        if nueva != var_repetir.get():
            lbl_error.config(text="Las contraseñas no coinciden.")
            return
        if nueva == db.PASSWORD_POR_DEFECTO:
            lbl_error.config(
                text="Elegí una contraseña distinta de la inicial.")
            return
        db.cambiar_password(usuario["id"], nueva)
        _cerrar(True)

    fila = tk.Frame(cont, bg=FONDO)
    fila.pack(fill="x", pady=(6, 0))
    Btn(fila, text="SALIR SIN CAMBIAR", command=lambda: _cerrar(False),
        bg="#3b4a6b", fg="#ffffff", font=(st.FUENTE, 10, "bold"),
        padx=14, pady=11).pack(side="left")
    Btn(fila, text="GUARDAR", command=guardar, bg=st.VERDE, fg="#ffffff",
        font=(st.FUENTE, 10, "bold"), padx=24, pady=11).pack(side="right")

    dlg.bind("<Return>", lambda e: guardar())
    try:
        dlg.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(dlg)
    return bool(getattr(dlg, "resultado", False))


def pedir_login(master):
    """Muestra el login y devuelve el usuario conectado, o None si se cancela.

    Si la contraseña con la que entró es la de fábrica ('admin'), antes de
    dejar pasar al usuario hay que crear una propia (hallazgo AppSec #3):
    si elige salir sin cambiarla, se cancela el ingreso."""
    dlg = LoginDialog(master)
    try:
        dlg.grab_set()          # modal: la ventana queda "agarrada"
    except tk.TclError:
        pass                    # si aún no se mapeó, wait_window alcanza
    master.wait_window(dlg)
    usuario = dlg.resultado
    if usuario is not None and db.es_password_inicial(usuario["password"]):
        if not cambiar_password_inicial(master, usuario):
            return None         # prefirió salir: no entra con "admin"
    return usuario
