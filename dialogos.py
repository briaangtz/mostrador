# -*- coding: utf-8 -*-
"""Ventanas de diálogo con el estilo del programa."""

import tkinter as tk

import estilos as st
import iconos as ic
from widgets_figma import Btn


def pedir_password(parent, usuario, titulo="Autenticación de cierre",
                   mensaje="Para cerrar la caja ingresá TU contraseña:",
                   subtitulo=None, icono="lock"):
    """Pide la contraseña del usuario conectado en una ventana propia.
    Devuelve el texto escrito, o None si se cancela."""
    dlg = tk.Toplevel(parent)
    dlg.title(titulo)
    dlg.configure(bg=st.FONDO)
    dlg.resizable(False, False)
    dlg.transient(parent)
    resultado = {"valor": None}

    cont = tk.Frame(dlg, bg=st.FONDO)
    cont.pack(fill="both", expand=True, padx=24, pady=22)
    cab = tk.Frame(cont, bg=st.FONDO)
    cab.pack(fill="x")
    tk.Label(cab, image=ic.cuadro(icono, 46, "#2563EB", "#E8F0FE", 12, 24, 1.8),
             bg=st.FONDO).pack(side="left", padx=(0, 14))
    col = tk.Frame(cab, bg=st.FONDO)
    col.pack(side="left")
    tk.Label(col, text=titulo, bg=st.FONDO, fg=st.TEXTO,
             font=(st.FUENTE, 14, "bold")).pack(anchor="w")
    if subtitulo:
        tk.Label(col, text=subtitulo, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 10)).pack(anchor="w")
    tk.Label(col, text=f"Usuario: {usuario}", bg=st.FONDO, fg=st.TEXTO_SUAVE,
             font=(st.FUENTE, 10)).pack(anchor="w")

    tk.Label(cont, text=mensaje, bg=st.FONDO, fg=st.TEXTO,
             font=(st.FUENTE, 10)).pack(anchor="w", pady=(16, 6))
    var = tk.StringVar()
    ent = tk.Entry(cont, textvariable=var, show="•", width=34,
                   font=(st.FUENTE, 12), relief="flat", bd=0, bg="#FFFFFF",
                   fg=st.TEXTO, insertbackground=st.TEXTO,
                   highlightthickness=1, highlightbackground="#D9E0EC",
                   highlightcolor=st.ACENTO)
    ent.pack(fill="x", ipady=8)

    def aceptar(_e=None):
        resultado["valor"] = var.get()
        dlg.destroy()

    def cancelar(_e=None):
        dlg.destroy()

    fila = tk.Frame(cont, bg=st.FONDO)
    fila.pack(fill="x", pady=(18, 0))
    Btn(fila, text="Cancelar", command=cancelar, bg="#E5EAF1", fg=st.TEXTO,
        font=(st.FUENTE, 10), padx=18, pady=9).pack(side="left")
    Btn(fila, text="CONFIRMAR", command=aceptar, bg=st.VERDE, fg="#ffffff",
        font=(st.FUENTE, 10, "bold"), padx=22, pady=9).pack(side="right")
    dlg.bind("<Return>", aceptar)
    dlg.bind("<Escape>", cancelar)
    dlg.protocol("WM_DELETE_WINDOW", cancelar)

    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    try:
        dlg.grab_set()
    except tk.TclError:
        pass
    ent.focus_set()
    parent.wait_window(dlg)
    return resultado["valor"]
