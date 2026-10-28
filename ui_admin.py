# -*- coding: utf-8 -*-
"""
Panel de Administración (solo rango DESARROLLADOR).

Alta, baja, modificación y activación/desactivación de usuarios,
asignación de rangos, contraseñas, consulta de permisos y
registro de actividad del sistema.
"""

import secrets
import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import estilos as st
import permisos as perms
import ui_comun as uc
from widgets_figma import Btn, Aviso

# Alfabeto sin caracteres confusos (0/O, 1/l/I) para contraseñas generadas
ALFABETO = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generar_password(largo=8):
    """Contraseña aleatoria segura (no se almacena en texto plano)."""
    return "".join(secrets.choice(ALFABETO) for _ in range(largo))


def generar_nombre_usuario(existentes):
    """Sugiere un nombre de usuario libre (usuario1, usuario2, ...)."""
    n = 1
    while f"usuario{n}" in existentes:
        n += 1
    return f"usuario{n}"


class AdminPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._usuarios = []
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        PX = 28
        MUTED = st.TEXTO_SUAVE
        INTERNO = "#F8FAFC"
        # Contenido con scroll: nada queda cortado en pantallas chicas
        contenido = st.contenido_scrollable(self)

        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 4))
        tk.Label(cab, text="Panel de control", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(cab,
                 text="Usuarios, rangos, contraseñas y registro de actividad "
                      "del sistema.",
                 bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 11)
                 ).pack(anchor="w", pady=(2, 0))

        self.lbl_sin_permiso = Aviso(contenido)
        self.lbl_sin_permiso.set(
            text="No tenés permisos para acceder al panel de administración.")

        def entrada(parent, var, ancho):
            return uc.entrada(parent, var, width=ancho)

        # ---------------- Usuarios ----------------
        self.marco_usuarios, cuerpo_u, _h = uc.tarjeta(
            contenido, "Usuarios del sistema", "user")
        self.marco_usuarios.pack(fill="x", padx=PX, pady=(14, 0))

        columnas = ("usuario", "rango", "estado", "creado", "acceso")
        self.tree = ttk.Treeview(cuerpo_u, columns=columnas,
                                 show="headings", height=5, selectmode="browse")
        for clave, texto, ancho, alin in (
            ("usuario", "Usuario", 170, "w"),
            ("rango", "Rango", 150, "w"),
            ("estado", "Estado", 100, "center"),
            ("creado", "Creado", 150, "center"),
            ("acceso", "Último acceso", 150, "center"),
        ):
            self.tree.heading(clave, text=texto)
            self.tree.column(clave, width=ancho, anchor=alin,
                             stretch=(clave in ("usuario", "rango")))
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._seleccionar)

        form = tk.Frame(cuerpo_u, bg=st.TARJETA)
        form.pack(fill="x", pady=(14, 0))

        def campo(parent, texto, ancho=16):
            c = tk.Frame(parent, bg=st.TARJETA)
            tk.Label(c, text=texto, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 9, "bold"), justify="left",
                     wraplength=170).pack(anchor="w")
            var = tk.StringVar()
            entrada(c, var, ancho).pack(anchor="w", pady=(3, 0), ipady=5)
            return var, c

        self.var_usuario, f1 = campo(form, "NOMBRE DE USUARIO", 18)
        self.var_password, f2 = campo(form, "CONTRASEÑA (se muestra para poder "
                                            "pasársela al usuario)", 18)

        c_rango = tk.Frame(form, bg=st.TARJETA)
        tk.Label(c_rango, text="RANGO", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.combo_rango = ttk.Combobox(c_rango, state="readonly", width=16,
                                        values=perms.RANGOS, font=(st.FUENTE, 11))
        self.combo_rango.pack(pady=(3, 0))
        self.combo_rango.set(perms.RANGOS[-1])

        c_activo = tk.Frame(form, bg=st.TARJETA)
        tk.Label(c_activo, text="ESTADO", bg=st.TARJETA, fg=MUTED,
                 font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.var_activo = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(c_activo, text="Usuario activo (puede ingresar)",
                             variable=self.var_activo, bg=st.TARJETA, fg=st.TEXTO,
                             font=(st.FUENTE, 10), anchor="w", cursor="hand2",
                             selectcolor="#ffffff", activebackground=st.TARJETA)
        chk.pack(pady=(8, 0), anchor="w")

        for w in (f1, f2, c_rango, c_activo):
            w.pack(side="left", anchor="n", padx=(0, 16))
        tk.Label(cuerpo_u, text="Seleccioná una fila de la lista para editarla.",
                 bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9)
                 ).pack(anchor="w", pady=(8, 0))

        # ---------------- Permisos individuales del usuario ----------------
        self.marco_permisos, cuerpo_p, _h = uc.tarjeta(
            cuerpo_u, "Permisos de este usuario", "lock", padx=14, pady=10)
        self.marco_permisos.pack(fill="x", pady=(14, 0))
        # tarjeta interna: fondo suave
        self.marco_permisos.pintar(fondo=INTERNO, exterior=st.TARJETA)
        for w in (cuerpo_p, _h) + tuple(_h.winfo_children()):
            try:
                w.configure(bg=INTERNO)
            except tk.TclError:
                pass

        self.lbl_nota_permisos = tk.Label(
            cuerpo_p, text="", bg=INTERNO, fg=MUTED,
            font=(st.FUENTE, 9), justify="left")
        self.lbl_nota_permisos.pack(anchor="w")

        self.chk_permisos = {}          # permiso -> (BooleanVar, Checkbutton)
        for nombre_grupo, claves in perms.GRUPOS:
            tk.Label(cuerpo_p, text=nombre_grupo.upper(), bg=INTERNO,
                     fg=st.ACENTO, font=(st.FUENTE, 8, "bold")).pack(
                anchor="w", pady=(8, 0))
            fila = tk.Frame(cuerpo_p, bg=INTERNO)
            fila.pack(fill="x")
            for i, p in enumerate(claves):
                var = tk.BooleanVar(value=False)
                chk = tk.Checkbutton(
                    fila, text=perms.ETIQUETAS.get(p, p), variable=var,
                    bg=INTERNO, fg=st.TEXTO, font=(st.FUENTE, 9), anchor="w",
                    selectcolor="#ffffff", activebackground=INTERNO,
                    padx=2, pady=1, cursor="hand2")
                fil, col = divmod(i, 3)
                fila.columnconfigure(col, weight=1)
                chk.grid(row=fil, column=col, sticky="w", padx=(0, 8), pady=1)
                self.chk_permisos[p] = (var, chk)

        self.combo_rango.bind("<<ComboboxSelected>>", lambda e: self._pintar_permisos())
        self._pintar_permisos()

        acciones = tk.Frame(cuerpo_u, bg=st.TARJETA)
        acciones.pack(fill="x", pady=(14, 0))

        self._btn(acciones, "Crear usuario", st.VERDE, self._crear).pack(
            side="left", padx=(0, 6))
        self._btn(acciones, "Guardar cambios", st.ACENTO, self._guardar).pack(
            side="left", padx=(0, 6))
        self._btn(acciones, "Activar / Desactivar", "#D97706",
                  self._activar_desactivar).pack(side="left", padx=(0, 6))
        self._btn(acciones, "Cambiar contraseña", "#7c3aed",
                  self._cambiar_password).pack(side="left", padx=(0, 6))
        self._btn(acciones, "Eliminar", st.ROJO, self._eliminar).pack(
            side="left")

        acciones2 = tk.Frame(cuerpo_u, bg=st.TARJETA)
        acciones2.pack(fill="x", pady=(8, 0))
        self._btn(acciones2, "Generar usuario", "#e5eaf1",
                  self._generar_usuario, texto_oscuro=True).pack(
            side="left", padx=(0, 6))
        self._btn(acciones2, "Generar contraseña", "#e5eaf1",
                  self._generar_password, texto_oscuro=True).pack(
            side="left", padx=(0, 6))
        self._btn(acciones2, "Ver permisos del rango", "#e5eaf1",
                  self._ver_permisos, texto_oscuro=True).pack(side="left")
        tk.Label(acciones2, text="Las contraseñas se guardan cifradas "
                                 "(nunca en texto plano).",
                 bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9),
                 justify="left", wraplength=260).pack(side="right")

        # ---------------- Registro de actividad ----------------
        self.marco_actividad, cuerpo_a, enc = uc.tarjeta(
            contenido, "Registro de actividad — quién hizo qué", "history")
        self.marco_actividad.pack(fill="both", expand=True, padx=PX,
                                  pady=(14, 24))
        self._btn(enc, "Actualizar", st.ACENTO,
                  self._refrescar_actividad).pack(side="right")
        tk.Label(cuerpo_a, text="Últimas acciones del sistema:",
                 bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9)
                 ).pack(anchor="w", pady=(0, 6))

        zona = tk.Frame(cuerpo_a, bg=st.TARJETA)
        zona.pack(fill="both", expand=True)
        columnas_act = ("fecha", "hora", "usuario", "accion", "detalle")
        self.tree_act = ttk.Treeview(zona, columns=columnas_act,
                                     show="headings", height=7,
                                     selectmode="browse")
        for clave, texto, ancho, alin in (
            ("fecha", "Fecha", 95, "center"),
            ("hora", "Hora", 80, "center"),
            ("usuario", "Usuario", 130, "w"),
            ("accion", "Acción", 175, "w"),
            ("detalle", "Detalle", 330, "w"),
        ):
            self.tree_act.heading(clave, text=texto)
            self.tree_act.column(clave, width=ancho, anchor=alin,
                                 stretch=(clave == "detalle"))
        scroll = ttk.Scrollbar(zona, orient="vertical",
                               command=self.tree_act.yview)
        self.tree_act.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree_act.pack(side="left", fill="both", expand=True)

    def _btn(self, parent, texto, color, comando, texto_oscuro=False):
        return Btn(parent, text=texto, command=comando, bg=color,
                   fg=st.TEXTO if texto_oscuro else "#ffffff",
                   font=(st.FUENTE, 9, "bold"), padx=14, pady=8)

    # ------------------------------------------------------------- acciones
    def _bloqueado(self):
        """True (y avisa) si la sesión actual no puede administrar usuarios."""
        if db.puede("admin_usuarios"):
            return False
        messagebox.showerror(
            "Sin permisos",
            "Solo un usuario con rango DESARROLLADOR puede administrar "
            "usuarios.", parent=self)
        return True

    def _seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Usuarios", "Seleccioná un usuario de la lista.",
                                   parent=self)
            return None
        return db.usuario_por_id(int(sel[0]))

    def _seleccionar(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        u = db.usuario_por_id(int(sel[0]))
        if not u:
            return
        self.var_usuario.set(u["usuario"])
        self.var_password.set("")          # nunca se muestra la contraseña guardada
        self.combo_rango.set(u["rango"])
        self.var_activo.set(bool(u["activo"]))
        self._pintar_permisos(db.permisos_efectivos(u["id"]))

    def _permisos_seleccionados(self):
        """Lista de permisos marcados en las casillas."""
        return [p for p, (var, _chk) in self.chk_permisos.items() if var.get()]

    def _pintar_permisos(self, permisos=None):
        """
        Marca las casillas según la lista indicada.
        Sin lista: usa los permisos del rango elegido en el combo.
        """
        rango = self.combo_rango.get() or perms.RANGOS[-1]
        es_dev = rango == "DESARROLLADOR"
        if permisos is None:
            permisos = (list(perms.PERMISOS) if es_dev
                        else perms.permisos_de(rango))
        conjunto = set(permisos)
        for p, (var, chk) in self.chk_permisos.items():
            var.set(es_dev or p in conjunto)
            chk.config(state="disabled" if es_dev else "normal")
        if es_dev:
            self.lbl_nota_permisos.config(
                text="El rango DESARROLLADOR tiene acceso completo a todo: "
                     "sus permisos no se modifican.")
        else:
            self.lbl_nota_permisos.config(
                text="Marcá exactamente qué puede hacer este usuario. "
                     "Los cambios se aplican al guardar.")

    def _crear(self):
        if self._bloqueado():
            return
        nombre = self.var_usuario.get().strip()
        password = self.var_password.get()
        rango = self.combo_rango.get()
        if not nombre:
            messagebox.showwarning("Usuarios", "Ingresá el nombre de usuario.",
                                   parent=self)
            return
        if len(password) < 4:
            messagebox.showerror(
                "Contraseña",
                "La contraseña debe tener al menos 4 caracteres.\n"
                "Usá «Generar contraseña» si querés una sugerida.",
                parent=self)
            return
        try:
            db.crear_usuario(nombre, password, rango,
                             permisos=self._permisos_seleccionados())
        except ValueError as exc:
            messagebox.showerror("Usuarios", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Usuario creado",
            f"Usuario «{nombre}» creado con rango {rango}.\n\n"
            f"Contraseña: {password}\n\nPasasela al usuario: él podrá "
            "cambiarla después.", parent=self)
        self.var_usuario.set("")
        self.var_password.set("")
        self._pintar_permisos()
        self.refresh()

    def _guardar(self):
        if self._bloqueado():
            return
        u = self._seleccionado()
        if not u:
            return
        activo = 1 if self.var_activo.get() else 0
        sesion = db.usuario_sesion()
        if activo == 0 and sesion and sesion["id"] == u["id"]:
            messagebox.showerror(
                "Usuarios", "No podés desactivar el usuario con el que estás "
                            "conectado.", parent=self)
            return
        try:
            db.actualizar_usuario(u["id"], usuario=self.var_usuario.get(),
                                  rango=self.combo_rango.get(), activo=activo,
                                  permisos=self._permisos_seleccionados())
        except ValueError as exc:
            messagebox.showerror("Usuarios", str(exc), parent=self)
            return
        messagebox.showinfo("Usuarios", "Cambios guardados correctamente.",
                            parent=self)
        self.refresh()
        self.app.refrescar_todo()

    def _activar_desactivar(self):
        if self._bloqueado():
            return
        u = self._seleccionado()
        if not u:
            return
        nuevo = 0 if u["activo"] else 1
        sesion = db.usuario_sesion()
        if nuevo == 0 and sesion and sesion["id"] == u["id"]:
            messagebox.showerror(
                "Usuarios", "No podés desactivar el usuario con el que estás "
                            "conectado.", parent=self)
            return
        try:
            db.actualizar_usuario(u["id"], activo=nuevo)
        except ValueError as exc:
            messagebox.showerror("Usuarios", str(exc), parent=self)
            return
        self.var_activo.set(bool(nuevo))
        self.refresh()

    def _eliminar(self):
        if self._bloqueado():
            return
        u = self._seleccionado()
        if not u:
            return
        if not messagebox.askyesno(
            "Eliminar usuario",
            f"¿Eliminar definitivamente al usuario «{u['usuario']}» "
            f"(rango {u['rango']})?\n\n"
            "El historial conservará la trazabilidad de sus operaciones.",
            parent=self,
        ):
            return
        try:
            db.eliminar_usuario(u["id"])
        except ValueError as exc:
            messagebox.showerror("Usuarios", str(exc), parent=self)
            return
        self.var_usuario.set("")
        self.var_password.set("")
        self.refresh()

    def _cambiar_password(self):
        if self._bloqueado():
            return
        u = self._seleccionado()
        if not u:
            return
        nueva = self._pedir_password(
            f"Cambiar contraseña — {u['usuario']}",
            "Ingresá la contraseña nueva para el usuario "
            f"«{u['usuario']}»:")
        if not nueva:
            return
        try:
            db.cambiar_password(u["id"], nueva)
        except ValueError as exc:
            messagebox.showerror("Contraseña", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Contraseña",
            f"Contraseña de «{u['usuario']}» actualizada.\n\n"
            f"Nueva contraseña: {nueva}", parent=self)

    def _pedir_password(self, titulo, mensaje):
        """Diálogo chico que devuelve una contraseña (visible para copiarla)."""
        dlg = tk.Toplevel(self)
        dlg.title(titulo)
        dlg.configure(bg=st.FONDO)
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        cont = tk.Frame(dlg, bg=st.FONDO)
        cont.pack(fill="both", expand=True, padx=20, pady=16)
        tk.Label(cont, text=mensaje, bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 10), justify="left").pack(anchor="w")
        var = tk.StringVar()
        ent = tk.Entry(cont, textvariable=var, width=26, font=(st.FUENTE, 13),
                       relief="flat", bd=0, highlightthickness=1,
                       highlightbackground="#D9E0EC", highlightcolor=st.ACENTO)
        ent.pack(fill="x", pady=(10, 6), ipady=4)

        valor = {}

        def ok():
            if len(var.get()) < 4:
                messagebox.showerror("Contraseña",
                                     "Mínimo 4 caracteres.", parent=dlg)
                return
            valor["v"] = var.get()
            dlg.destroy()

        def cancelar():
            dlg.destroy()

        fila = tk.Frame(cont, bg=st.FONDO)
        fila.pack(fill="x", pady=(8, 0))
        Btn(fila, text="Cancelar", command=cancelar, relief="flat",
                  bg="#e5eaf1", fg=st.TEXTO, font=(st.FUENTE, 10), padx=14,
                  pady=7, cursor="hand2").pack(side="left")
        Btn(fila, text="Guardar", command=ok, relief="flat", bg=st.VERDE,
                  fg="#ffffff", font=(st.FUENTE, 10, "bold"), padx=16, pady=7,
                  cursor="hand2").pack(side="right")

        dlg.bind("<Return>", lambda e: ok())
        ent.focus_set()
        self.wait_window(dlg)
        return valor.get("v")

    def _generar_usuario(self):
        if self._bloqueado():
            return
        existentes = [u["usuario"].lower() for u in db.listar_usuarios()]
        self.var_usuario.set(generar_nombre_usuario(existentes))

    def _generar_password(self):
        if self._bloqueado():
            return
        self.var_password.set(generar_password())

    def _ver_permisos(self):
        rango = self.combo_rango.get() or perms.RANGOS[-1]
        dlg = tk.Toplevel(self)
        dlg.title(f"Permisos del rango {rango}")
        dlg.configure(bg=st.FONDO)
        dlg.geometry("560x520")
        dlg.transient(self)
        dlg.grab_set()

        cont = tk.Frame(dlg, bg=st.FONDO)
        cont.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(cont, text=f"PERMISOS — {rango}", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 16, "bold")).pack(anchor="w")
        tk.Label(cont,
                 text="Permisos por defecto del rango. Cada usuario puede "
                      "tener permisos propios (se marcan en las casillas de "
                      "la lista de usuarios).",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)).pack(
            anchor="w", pady=(0, 10))

        frame = tk.Frame(cont, bg=st.TARJETA, highlightbackground=st.BORDE,
                         highlightthickness=1)
        frame.pack(fill="both", expand=True)

        for permiso in perms.PERMISOS:
            tiene = perms.puede(permiso, rango)
            fila = tk.Frame(frame, bg=st.TARJETA)
            fila.pack(fill="x", padx=10, pady=3)
            tk.Label(fila, text="✓" if tiene else "—", bg=st.TARJETA,
                     fg=st.VERDE_OSCURO if tiene else st.TEXTO_SUAVE,
                     font=(st.FUENTE, 11, "bold"), width=2).pack(side="left")
            tk.Label(fila, text=perms.DESCRIPCIONES.get(permiso, permiso),
                     bg=st.TARJETA, fg=st.TEXTO if tiene else st.TEXTO_SUAVE,
                     font=(st.FUENTE, 10), anchor="w", justify="left").pack(
                side="left", fill="x", expand=True)

        Btn(cont, text="Cerrar", command=dlg.destroy, relief="flat",
                  bg="#e5eaf1", fg=st.TEXTO, font=(st.FUENTE, 10), padx=18,
                  pady=8, cursor="hand2").pack(anchor="e", pady=(12, 0))

    def _refrescar_actividad(self):
        self.tree_act.delete(*self.tree_act.get_children())
        for a in db.historial_actividad():
            fecha, hora = (a["fecha_hora"].split(" ") + [""])[:2]
            self.tree_act.insert("", "end", values=(
                fecha[:10], hora[:8], a["usuario"] or "—",
                a["accion"], a["detalle"] or "",
            ))

    # ------------------------------------------------------------- refresco
    def refresh(self):
        if not db.puede("panel_admin"):
            self.marco_usuarios.pack_forget()
            self.marco_actividad.pack_forget()
            self.lbl_sin_permiso.pack(fill="x", padx=28, pady=(14, 0))
            return
        self.lbl_sin_permiso.pack_forget()
        self.marco_usuarios.pack(fill="x", padx=28, pady=(14, 0))
        self.marco_actividad.pack(fill="both", expand=True, padx=28,
                                  pady=(14, 24))

        # Listado de usuarios
        seleccion = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self._usuarios = db.listar_usuarios()
        for u in self._usuarios:
            iid = str(u["id"])
            self.tree.insert("", "end", iid=iid, values=(
                u["usuario"],
                u["rango"],
                "Activo" if u["activo"] else "Inactivo",
                (u["creado"] or "")[:16],
                (u["ultimo_acceso"] or "—")[:16],
            ))
            self.tree.tag_configure("inactivo",
                                    foreground=st.ROJO if not u["activo"]
                                    else st.VERDE_OSCURO)
            if not u["activo"]:
                self.tree.item(iid, tags=("inactivo",))
        if seleccion and self.tree.exists(seleccion[0]):
            self.tree.selection_set(seleccion[0])

        self._refrescar_actividad()
