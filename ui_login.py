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
        tk.Label(col, text="GARRAFAS", bg=FONDO, fg="#ffffff",
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


def pedir_login(master):
    """Muestra el login y devuelve el usuario conectado, o None si se cancela."""
    dlg = LoginDialog(master)
    try:
        dlg.grab_set()          # modal: la ventana queda "agarrada"
    except tk.TclError:
        pass                    # si aún no se mapeó, wait_window alcanza
    master.wait_window(dlg)
    return dlg.resultado
