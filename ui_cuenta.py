# -*- coding: utf-8 -*-
"""Panel MI CUENTA: foto de perfil, datos del usuario y contraseña."""

import os
import tkinter as tk
from tkinter import messagebox, filedialog

import database as db
import errores
import estilos as st
import iconos as ic
import ui_comun as uc
from widgets_figma import Btn


class CuentaPanel(tk.Frame):
    """Perfil del usuario conectado: foto desde el escritorio, datos y clave."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._foto_ref = None      # conserva la imagen Tk (si no, no se ve)
        self._construir()

    def _construir(self):
        PX = 28
        MUTED = st.TEXTO_SUAVE
        # ---------------- Cabecera ----------------
        cab = tk.Frame(self, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 4))
        tk.Label(cab, text="Mi cuenta", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(cab, text="Tu perfil, tu foto y tu contraseña.",
                 bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 11)
                 ).pack(anchor="w", pady=(2, 0))

        cuerpo = tk.Frame(self, bg=st.FONDO)
        cuerpo.pack(fill="both", expand=True, padx=PX, pady=(14, 24))

        def entrada(parent, var, ancho, **kw):
            return uc.entrada(parent, var, width=ancho, **kw)

        # ---------------- Columna izquierda: foto ----------------
        t_foto, marco_foto, _h = uc.tarjeta(cuerpo, "Foto de perfil", "user",
                                            padx=20, pady=16)
        t_foto.configure(width=270)
        t_foto.pack(side="left", anchor="n")

        self.lbl_foto = tk.Label(marco_foto, text="", bg=st.TARJETA)
        self.lbl_foto.pack(pady=(4, 14))

        self._boton(marco_foto, "Elegir imagen…", st.ACENTO,
                    self._elegir_imagen).pack(fill="x", pady=(0, 6))
        self._boton(marco_foto, "Quitar foto", "#e5eaf1",
                    self._quitar_foto).pack(fill="x")

        tk.Label(marco_foto,
                 text="Podés elegir una imagen\ndel Escritorio (JPG, PNG,\n"
                      "BMP o ICO).",
                 bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9),
                 justify="left").pack(anchor="w", pady=(12, 0))

        # ---------------- Columna derecha: datos ----------------
        der = tk.Frame(cuerpo, bg=st.FONDO)
        der.pack(side="left", fill="both", expand=True, padx=(14, 0))

        t_datos, marco_datos, _h = uc.tarjeta(der, "Tus datos", "doc")
        t_datos.pack(fill="x")

        self.datos = {}
        for clave, etiqueta in (("usuario", "Usuario"),
                                ("rango", "Rango"),
                                ("ultimo_acceso", "Último acceso"),
                                ("creado", "Miembro desde")):
            f, lbl = uc.fila(marco_datos, etiqueta, "—", tam=11)
            # En esta pantalla el valor va pegado al rótulo (a la izquierda)
            lbl.pack_forget()
            lbl.configure(anchor="w", justify="left", font=(st.FUENTE, 11, "bold"))
            lbl.pack(side="left", padx=(0, 0))
            f.winfo_children()[0].configure(width=16, fg=MUTED,
                                            font=(st.FUENTE, 10, "bold"))
            self.datos[clave] = lbl

        # ---------------- Cambiar contraseña ----------------
        t_seg, marco_seg, _h = uc.tarjeta(der, "Cambiar mi contraseña", "lock")
        t_seg.pack(fill="x", pady=(14, 0))

        fila_seg = tk.Frame(marco_seg, bg=st.TARJETA)
        fila_seg.pack(fill="x")

        def campo(texto):
            c = tk.Frame(fila_seg, bg=st.TARJETA)
            tk.Label(c, text=texto, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar()
            entrada(c, var, 18, show="•").pack(anchor="w", pady=(3, 0), ipady=5)
            return var, c

        self.var_actual, f1 = campo("CONTRASEÑA ACTUAL")
        self.var_nueva, f2 = campo("NUEVA CONTRASEÑA")
        self.var_repetir, f3 = campo("REPETIR NUEVA CONTRASEÑA")
        f1.pack(side="left")
        f2.pack(side="left", padx=(16, 0))
        f3.pack(side="left", padx=(16, 0))

        cbtn = tk.Frame(marco_seg, bg=st.TARJETA)
        cbtn.pack(fill="x", pady=(14, 0))
        self._boton(cbtn, "Guardar contraseña", st.VERDE,
                    self._cambiar_password).pack(side="left")

        tk.Label(marco_seg,
                 text="Es la contraseña con la que te identificás: se te pide "
                      "para iniciar sesión, cerrar o reabrir una caja.",
                 bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9),
                 ).pack(anchor="w", pady=(10, 0))

        # ---------------- Cierre de sesión ----------------
        fila_salir = tk.Frame(der, bg=st.FONDO)
        fila_salir.pack(fill="x", pady=(14, 0))
        self._boton(fila_salir, "Cerrar sesión", st.ROJO,
                    self.app.cerrar_sesion).pack(side="right")

    # ------------------------------------------------------------- helpers
    def _boton(self, parent, texto, color, comando):
        gris = color == "#e5eaf1"
        return Btn(parent, text=texto, command=comando, bg=color,
                   fg=st.TEXTO if gris else "#ffffff",
                   font=(st.FUENTE, 10, "bold"), padx=16, pady=9)

    # ------------------------------------------------------------- acciones
    def _elegir_imagen(self):
        if not db.puede("cambiar_mia_clave"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no puede modificar el perfil.",
                                 parent=self)
            return
        escritorio = os.path.expanduser("~\\Desktop")
        if not os.path.isdir(escritorio):
            escritorio = os.path.expanduser("~")
        ruta = filedialog.askopenfilename(
            title="Elegir foto de perfil",
            initialdir=escritorio,
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif *.ico"),
                       ("Todos los archivos", "*.*")],
            parent=self,
        )
        if not ruta:
            return
        try:
            db.set_foto_perfil(ruta)
        except Exception as exc:
            errores.mostrar(
                "No se pudo cargar la imagen", exc, parent=self,
                contexto="cargar foto de perfil",
                mensaje="No se pudo cargar la imagen.\n"
                        "Probá con un PNG o JPG más liviano.")
            return
        self.refresh()
        self.app.refrescar_todo()      # actualiza la foto del lateral

    def _quitar_foto(self):
        if not db.foto_perfil():
            return
        if not messagebox.askyesno("Quitar foto",
                                   "¿Eliminar tu foto de perfil?",
                                   parent=self):
            return
        db.quitar_foto_perfil()
        self.refresh()
        self.app.refrescar_todo()

    def _cambiar_password(self):
        if not db.puede("cambiar_mia_clave"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no puede modificar contraseñas.",
                                 parent=self)
            return
        actual = self.var_actual.get()
        nueva = self.var_nueva.get()
        repetir = self.var_repetir.get()

        if not db.validar_password_sesion(actual):
            messagebox.showerror("Seguridad", "La contraseña actual no es correcta.",
                                 parent=self)
            return
        if len(nueva) < 4:
            messagebox.showerror("Seguridad",
                                 "La nueva contraseña debe tener al menos 4 caracteres.",
                                 parent=self)
            return
        if nueva != repetir:
            messagebox.showerror("Seguridad",
                                 "La nueva contraseña no coincide con la repetición.",
                                 parent=self)
            return
        u = db.usuario_sesion()
        try:
            db.cambiar_password(u["id"], nueva)
        except ValueError as exc:
            messagebox.showerror("Seguridad", str(exc), parent=self)
            return
        self.var_actual.set("")
        self.var_nueva.set("")
        self.var_repetir.set("")
        messagebox.showinfo("Seguridad", "Contraseña cambiada correctamente.",
                            parent=self)

    # ------------------------------------------------------------- refresco
    def _pintar_foto(self):
        """Foto de perfil en círculo; si no hay, un círculo con la inicial."""
        ruta = db.foto_perfil()
        foto = None
        if ruta:
            try:
                foto = ic.foto_circular(ruta, 160)
            except Exception:
                foto = None
        if foto is None:
            try:
                u = db.usuario_sesion()
                inicial = (u["usuario"][:1] or "?").upper()
            except Exception:
                inicial = "?"
            foto = ic.avatar(inicial, 160, "#2B4A7A", "#FFFFFF", 0.42)
        self._foto_ref = foto
        self.lbl_foto.config(image=foto, text="")

    def refresh(self):
        u = db.usuario_sesion()
        if not u:
            return
        self.datos["usuario"].config(text=u["usuario"])
        self.datos["rango"].config(text=u["rango"])
        self.datos["ultimo_acceso"].config(
            text=u["ultimo_acceso"] or "—")
        self.datos["creado"].config(text=u["creado"] or "—")
        self._pintar_foto()
