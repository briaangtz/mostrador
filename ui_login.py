# -*- coding: utf-8 -*-
"""Pantalla de inicio de sesión (obligatoria para usar el sistema)."""

import tkinter as tk

import database as db
import estilos as st


class LoginDialog(tk.Toplevel):
    """Ventana modal de usuario + contraseña."""

    def __init__(self, master):
        super().__init__(master)
        self.resultado = None

        self.title("Iniciar sesión")
        self.configure(bg=st.BARRA)
        self.resizable(False, False)
        # NOTA: no usar transient(master): la raíz está oculta (withdraw)
        # esperando el login y Windows no dibuja una ventana transient
        # cuyo dueño está oculta. La modalidad la da wait_window + grab.
        self.protocol("WM_DELETE_WINDOW", self._salir)

        ancho, alto = 430, 380
        self.geometry(f"{ancho}x{alto}")
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2 - 40)
        self.geometry(f"+{x}+{y}")
        self.lift()
        self.focus_force()

        cont = tk.Frame(self, bg=st.BARRA)
        cont.pack(fill="both", expand=True, padx=36, pady=(34, 26))

        tk.Label(cont, text="GARRAFAS", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 26, "bold")).pack(anchor="w")
        tk.Label(cont, text="Control de caja diaria — inicio de sesión",
                 bg=st.BARRA, fg="#9fb0cc", font=(st.FUENTE, 10)).pack(
            anchor="w", pady=(0, 24))

        def campo(texto, mostrar=""):
            tk.Label(cont, text=texto, bg=st.BARRA, fg="#c7d2e4",
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar()
            ent = tk.Entry(cont, textvariable=var, font=(st.FUENTE, 13),
                           relief="solid", bd=1, show=mostrar)
            ent.pack(fill="x", pady=(4, 14), ipady=5)
            return var, ent

        self.var_usuario, self.ent_usuario = campo("USUARIO")
        self.var_password, self.ent_password = campo("CONTRASEÑA", mostrar="•")

        self.lbl_error = tk.Label(cont, text="", bg=st.BARRA, fg="#fca5a5",
                                  font=(st.FUENTE, 9), anchor="w", justify="left")
        self.lbl_error.pack(fill="x")

        fila = tk.Frame(cont, bg=st.BARRA)
        fila.pack(fill="x", pady=(16, 0))

        btnSalir = tk.Button(fila, text="SALIR", command=self._salir,
                             relief="flat", bg="#3b4a6b", fg="#ffffff",
                             font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
                             cursor="hand2")
        btnSalir.pack(side="left", fill="x", expand=True)

        btnIngresar = tk.Button(fila, text="INGRESAR", command=self._ingresar,
                                relief="flat", bg=st.VERDE, fg="#ffffff",
                                font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
                                cursor="hand2")
        btnIngresar.pack(side="left", fill="x", expand=True, padx=(10, 0))
        btnIngresar.bind("<Enter>", lambda e: btnIngresar.config(bg=st.VERDE_OSCURO))
        btnIngresar.bind("<Leave>", lambda e: btnIngresar.config(bg=st.VERDE))

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
