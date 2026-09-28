# -*- coding: utf-8 -*-
"""Panel MI CUENTA: foto de perfil, datos del usuario y contraseña."""

import os
import tkinter as tk
from tkinter import messagebox, filedialog

import database as db
import estilos as st


class CuentaPanel(tk.Frame):
    """Perfil del usuario conectado: foto desde el escritorio, datos y clave."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._foto_ref = None      # conserva la imagen Tk (si no, no se ve)
        self._construir()

    def _construir(self):
        # ---------------- Cabecera ----------------
        cab = tk.Frame(self, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(cab, text="MI CUENTA", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        tk.Label(cab, text="Tu perfil, tu foto y tu contraseña.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 11)).pack(anchor="w")

        cuerpo = tk.Frame(self, bg=st.FONDO)
        cuerpo.pack(fill="both", expand=True, padx=24, pady=(14, 24))

        # ---------------- Columna izquierda: foto ----------------
        marco_foto = st.labelframe(cuerpo, " FOTO DE PERFIL ", padx=16, pady=14)
        marco_foto.pack(side="left", fill="y", anchor="n")

        self.lbl_foto = tk.Label(marco_foto, text="Sin foto\n(Elegí una imagen)",
                                 bg="#1e293b", fg="#9fb0cc",
                                 font=(st.FUENTE, 10), width=20, height=9,
                                 justify="center")
        self.lbl_foto.pack(pady=(0, 12))

        self._boton(marco_foto, "Elegir imagen…", st.ACENTO,
                    self._elegir_imagen).pack(fill="x", pady=(0, 6))
        self._boton(marco_foto, "Quitar foto", "#64748b",
                    self._quitar_foto).pack(fill="x")

        tk.Label(marco_foto,
                 text="Podés elegir una imagen\ndel Escritorio (JPG, PNG,\n"
                      "BMP o ICO).",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 8),
                 justify="left").pack(anchor="w", pady=(10, 0))

        # ---------------- Columna derecha: datos ----------------
        der = tk.Frame(cuerpo, bg=st.FONDO)
        der.pack(side="left", fill="both", expand=True, padx=(16, 0))

        marco_datos = st.labelframe(der, " TUS DATOS ", padx=16, pady=14)
        marco_datos.pack(fill="x")

        self.datos = {}
        for clave, etiqueta in (("usuario", "Usuario"),
                                ("rango", "Rango"),
                                ("ultimo_acceso", "Último acceso"),
                                ("creado", "Miembro desde")):
            fila = tk.Frame(marco_datos, bg=st.FONDO)
            fila.pack(fill="x", pady=3)
            tk.Label(fila, text=etiqueta + ":", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 10, "bold"), width=16, anchor="w").pack(
                side="left")
            lbl = tk.Label(fila, text="—", bg=st.FONDO, fg=st.TEXTO,
                           font=(st.FUENTE, 11), anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self.datos[clave] = lbl

        # ---------------- Cambiar contraseña ----------------
        marco_seg = st.labelframe(der, " CAMBIAR MI CONTRASEÑA ", padx=16, pady=14)
        marco_seg.pack(fill="x", pady=(14, 0))

        fila_seg = tk.Frame(marco_seg, bg=st.FONDO)
        fila_seg.pack(fill="x")

        def campo(texto):
            c = tk.Frame(fila_seg, bg=st.FONDO)
            tk.Label(c, text=texto, bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")
            var = tk.StringVar()
            tk.Entry(c, textvariable=var, show="•", width=18,
                     font=(st.FUENTE, 11), relief="solid", bd=1).pack(
                pady=(3, 0), ipady=3)
            return var, c

        self.var_actual, f1 = campo("Contraseña actual")
        self.var_nueva, f2 = campo("Nueva contraseña")
        self.var_repetir, f3 = campo("Repetir nueva contraseña")
        f1.pack(side="left")
        f2.pack(side="left", padx=(16, 0))
        f3.pack(side="left", padx=(16, 0))

        cbtn = tk.Frame(fila_seg, bg=st.FONDO)
        cbtn.pack(side="left", padx=(20, 0), anchor="s")
        tk.Label(cbtn, text="", bg=st.FONDO).pack()
        self._boton(cbtn, "Guardar contraseña", st.VERDE,
                    self._cambiar_password).pack(pady=(16, 0))

        tk.Label(marco_seg,
                 text="Es la contraseña con la que te identificás: se te pide "
                      "para iniciar sesión, cerrar o reabrir una caja.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9),
                 ).pack(anchor="w", pady=(8, 0))

        # ---------------- Cierre de sesión ----------------
        fila_salir = tk.Frame(der, bg=st.FONDO)
        fila_salir.pack(fill="x", pady=(14, 0))
        self._boton(fila_salir, "Cerrar sesión", st.ROJO,
                    self.app.cerrar_sesion).pack(side="right")

    # ------------------------------------------------------------- helpers
    def _boton(self, parent, texto, color, comando):
        return tk.Button(parent, text=texto, command=comando, relief="flat",
                         bg=color, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
                         padx=14, pady=8, cursor="hand2")

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
            messagebox.showerror("No se pudo cargar la imagen", str(exc),
                                 parent=self)
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
        ruta = db.foto_perfil()
        if not ruta:
            self.lbl_foto.config(image="", text="Sin foto\n(Elegí una imagen)")
            self._foto_ref = None
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(ruta).convert("RGB")
            w, h = img.size
            lado = min(w, h)
            img = img.crop(((w - lado) // 2, (h - lado) // 2,
                            (w + lado) // 2, (h + lado) // 2))
            img = img.resize((160, 160), Image.LANCZOS)
            foto = ImageTk.PhotoImage(img)
        except Exception:
            self.lbl_foto.config(image="", text="No se pudo\nmostrar la foto")
            self._foto_ref = None
            return
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
