# -*- coding: utf-8 -*-
"""Panel de configuración: precios de productos, fondo inicial, respaldos y contraseña."""

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import database as db
import errores
import estilos as st
import ui_comun as uc
from util import money, parse_numero
from widgets_figma import Btn, Aviso


class ConfigPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._construir()

    def _construir(self):
        PX = 28
        MUTED = st.TEXTO_SUAVE
        # Contenido con scroll: nada queda cortado en pantallas chicas
        contenido = st.contenido_scrollable(self)

        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 4))
        tk.Label(cab, text="Configuración", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(cab, text="Precios de las garrafas, fondo inicial de caja, "
                           "respaldos y tu contraseña personal.",
                 bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 11)
                 ).pack(anchor="w", pady=(2, 0))

        cuerpo = tk.Frame(contenido, bg=st.FONDO)
        cuerpo.pack(fill="both", expand=True, padx=PX, pady=(14, 24))

        # Va dentro de "cuerpo": así el empaquetado con before= (más abajo)
        # tiene el mismo padre que el bloque "Mi cuenta" y no falla.
        self.lbl_sin_permiso = Aviso(cuerpo, fondo="#FFF7E0", borde="#F8D98B",
                                     color="#B45309", icono="info")
        self.lbl_sin_permiso.set(
            text="Los precios de productos y el fondo inicial los modifica "
                 "únicamente un DESARROLLADOR.")

        def entrada(parent, var, ancho, **kw):
            return uc.entrada(parent, var, width=ancho, **kw)

        def etiqueta(parent, texto):
            tk.Label(parent, text=texto, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 9, "bold")).pack(anchor="w")

        # ---------------- Productos ----------------
        marco_prod, cuerpo_prod, _h = uc.tarjeta(cuerpo, "Productos y precios",
                                                 "cube")
        marco_prod.pack(fill="both", expand=True)

        # Con barra propia: con muchos productos ninguno queda fuera de vista
        marco_lista = tk.Frame(cuerpo_prod, bg=st.TARJETA)
        marco_lista.pack(fill="both", expand=True)
        scroll_prod = ttk.Scrollbar(marco_lista, orient="vertical")
        scroll_prod.pack(side="right", fill="y")
        self.tree = ttk.Treeview(marco_lista, columns=("producto", "precio"),
                                 show="headings", height=6, selectmode="browse",
                                 yscrollcommand=scroll_prod.set)
        self.tree.heading("producto", text="Producto")
        self.tree.heading("precio", text="Precio unitario")
        self.tree.column("producto", width=320, anchor="w")
        self.tree.column("precio", width=160, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_prod.config(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._seleccionar)

        form = tk.Frame(cuerpo_prod, bg=st.TARJETA)
        form.pack(fill="x", pady=(14, 0))

        c1 = tk.Frame(form, bg=st.TARJETA)
        c1.pack(side="left")
        etiqueta(c1, "NOMBRE DEL PRODUCTO")
        self.var_nombre = tk.StringVar()
        entrada(c1, self.var_nombre, 26).pack(anchor="w", pady=(3, 0), ipady=5)

        c2 = tk.Frame(form, bg=st.TARJETA)
        c2.pack(side="left", padx=(16, 0))
        etiqueta(c2, "PRECIO UNITARIO ($)")
        self.var_precio = tk.StringVar()
        entrada(c2, self.var_precio, 14).pack(anchor="w", pady=(3, 0), ipady=5)

        botones = tk.Frame(form, bg=st.TARJETA)
        botones.pack(side="left", padx=(20, 0), anchor="s", pady=(0, 1))
        self._boton(botones, "Guardar cambios", st.ACENTO,
                    self._guardar_producto).pack(side="left", padx=(0, 6))
        self._boton(botones, "Nuevo producto", st.VERDE,
                    self._nuevo_producto).pack(side="left", padx=(0, 6))
        self._boton(botones, "Eliminar", st.ROJO,
                    self._eliminar_producto).pack(side="left")

        # ---------------- Fondo inicial ----------------
        marco_fondo, cuerpo_fondo, _h = uc.tarjeta(cuerpo, "Caja", "banknote")
        marco_fondo.pack(fill="x", pady=(14, 0))

        fila = tk.Frame(cuerpo_fondo, bg=st.TARJETA)
        fila.pack(fill="x")
        tk.Label(fila, text="Fondo inicial de efectivo (cambio para vender):",
                 bg=st.TARJETA, fg=st.TEXTO, font=(st.FUENTE, 10)
                 ).pack(side="left")
        self.var_fondo = tk.StringVar()
        entrada(fila, self.var_fondo, 14).pack(side="left", padx=12, ipady=5)
        self._boton(fila, "Guardar fondo", st.ACENTO,
                    self._guardar_fondo).pack(side="left")
        tk.Label(
            cuerpo_fondo,
            text="Se suma al efectivo esperado al momento del arqueo "
                 "(efectivo esperado = ventas en efectivo + fondo inicial).",
            bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9),
        ).pack(anchor="w", pady=(10, 0))

        # ---------------- Respaldo de la base ----------------
        marco_respaldo, cuerpo_resp, _h = uc.tarjeta(
            cuerpo, "Respaldo de la base de datos", "doc")
        marco_respaldo.pack(fill="x", pady=(14, 0))

        self.lbl_ultimo_respaldo = tk.Label(
            cuerpo_resp, text="", bg=st.TARJETA, fg=st.TEXTO,
            font=(st.FUENTE, 10, "bold"), anchor="w")
        self.lbl_ultimo_respaldo.pack(anchor="w")

        fila_auto = tk.Frame(cuerpo_resp, bg=st.TARJETA)
        fila_auto.pack(fill="x", pady=(10, 0))
        self.var_respaldo_auto = tk.BooleanVar(
            value=db.respaldo_automatico_activo())
        tk.Checkbutton(
            fila_auto,
            text="Respaldar automáticamente (uno por día al abrir y al cerrar "
                 "el programa, y en cada cierre de caja)",
            variable=self.var_respaldo_auto,
            command=self._toggle_respaldo, bg=st.TARJETA, fg=st.TEXTO,
            font=(st.FUENTE, 10), anchor="w", selectcolor="#ffffff",
            activebackground=st.TARJETA, cursor="hand2",
        ).pack(anchor="w")

        botones_r = tk.Frame(cuerpo_resp, bg=st.TARJETA)
        botones_r.pack(fill="x", pady=(12, 0))
        self._boton(botones_r, "Respaldar ahora", st.ACENTO,
                    self._respaldar_ahora).pack(side="left", padx=(0, 6))
        self._boton(botones_r, "Abrir carpeta de respaldos", "#e5eaf1",
                    self._abrir_carpeta).pack(side="left", padx=(0, 6))
        self._boton(botones_r, "Restaurar respaldo…", st.ROJO,
                    self._restaurar_respaldo).pack(side="left")

        tk.Label(
            cuerpo_resp,
            text="Los respaldos se guardan en la carpeta «respaldos», junto al "
                 "programa (se conservan los últimos 60). Para restaurar, "
                 "elegí un archivo y reiniciá el programa.",
            bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9), wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

        # ---------------- Seguridad ----------------
        marco_seg, cuerpo_seg, _h = uc.tarjeta(
            cuerpo, "Mi cuenta — cambiar mi contraseña", "lock")
        marco_seg.pack(fill="x", pady=(14, 0))

        fila_seg = tk.Frame(cuerpo_seg, bg=st.TARJETA)
        fila_seg.pack(fill="x")

        def campo(parent, texto):
            c = tk.Frame(parent, bg=st.TARJETA)
            etiqueta(c, texto)
            var = tk.StringVar()
            entrada(c, var, 16, show="•").pack(anchor="w", pady=(3, 0), ipady=5)
            return var, c

        self.var_actual, f1 = campo(fila_seg, "CONTRASEÑA ACTUAL")
        self.var_nueva, f2 = campo(fila_seg, "NUEVA CONTRASEÑA")
        self.var_repetir, f3 = campo(fila_seg, "REPETIR NUEVA CONTRASEÑA")

        f1.pack(side="left")
        f2.pack(side="left", padx=(16, 0))
        f3.pack(side="left", padx=(16, 0))
        cbtn = tk.Frame(fila_seg, bg=st.TARJETA)
        cbtn.pack(side="left", padx=(20, 0), anchor="s", pady=(0, 1))
        self._boton(cbtn, "Cambiar contraseña", st.ACENTO,
                    self._cambiar_password).pack()

        tk.Label(
            cuerpo_seg,
            text="Es la contraseña con la que te identificás: se te pide para "
                 "iniciar sesión, cerrar o reabrir una caja.",
            bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9),
        ).pack(anchor="w", pady=(10, 0))

        # Guardamos los marcos para mostrarlos/ocultarlos según el rango
        self.marco_prod = marco_prod
        self.marco_fondo = marco_fondo
        self.marco_respaldo = marco_respaldo
        self.marco_seg = marco_seg
        self._aplicar_permisos()

    def _aplicar_permisos(self):
        """Precios, fondo y respaldos: solo DESARROLLADOR. Contraseña propia: todos."""
        if db.puede("configuracion"):
            self.lbl_sin_permiso.pack_forget()
            # before= mantiene el orden aunque se vuelva a mostrar
            if not self.marco_prod.winfo_ismapped():
                self.marco_prod.pack(fill="both", expand=True,
                                     before=self.marco_seg)
            if not self.marco_fondo.winfo_ismapped():
                self.marco_fondo.pack(fill="x", pady=(14, 0),
                                      before=self.marco_seg)
            if not self.marco_respaldo.winfo_ismapped():
                self.marco_respaldo.pack(fill="x", pady=(14, 0),
                                         before=self.marco_seg)
        else:
            self.marco_prod.pack_forget()
            self.marco_fondo.pack_forget()
            self.marco_respaldo.pack_forget()
            self.lbl_sin_permiso.pack(fill="x", pady=(14, 0), before=self.marco_seg)

    def _boton(self, parent, texto, color, comando):
        gris = color == "#e5eaf1"
        return Btn(parent, text=texto, command=comando, bg=color,
                   fg=st.TEXTO if gris else "#ffffff",
                   font=(st.FUENTE, 10, "bold"), padx=16, pady=8)

    # ------------------------------------------------------------ respaldos
    def _refrescar_respaldo(self):
        info = db.ultimo_respaldo()
        total = len(db.respaldos_existentes())
        if info:
            texto = (f"Último respaldo: {info['fecha'].strftime('%d/%m/%Y %H:%M')}"
                     f" — {max(1, info['tamano'] // 1024)} KB — "
                     f"{total} respaldo(s) guardados")
        else:
            texto = "Todavía no hay respaldos. Presioná «Respaldar ahora»."
        self.lbl_ultimo_respaldo.config(text=texto)

    def _toggle_respaldo(self):
        if not db.puede("configuracion"):
            self.var_respaldo_auto.set(db.respaldo_automatico_activo())
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR cambia esta opción.",
                                 parent=self)
            return
        activo = bool(self.var_respaldo_auto.get())
        db.set_respaldo_automatico(activo)
        db.log_actividad("Respaldo automático",
                         "activado" if activo else "desactivado")

    def _respaldar_ahora(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR genera respaldos.",
                                 parent=self)
            return
        try:
            ruta = db.respaldar("manual desde configuración")
        except Exception as exc:
            errores.mostrar(
                "Respaldo", exc, parent=self, contexto="generar respaldo",
                mensaje="No se pudo generar el respaldo.\n"
                        "Revisá que el disco tenga espacio libre.")
            return
        kb = max(1, os.path.getsize(ruta) // 1024)
        messagebox.showinfo(
            "Respaldo generado",
            f"Respaldo creado correctamente.\n\n{os.path.basename(ruta)}\n"
            f"{kb} KB\n\nCarpeta: {db.dir_respaldos()}",
            parent=self)
        self._refrescar_respaldo()

    def _abrir_carpeta(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR accede a los respaldos.",
                                 parent=self)
            return
        carpeta = db.dir_respaldos()
        os.makedirs(carpeta, exist_ok=True)
        try:
            os.startfile(carpeta)          # abre el explorador de Windows
        except OSError as exc:
            errores.mostrar(
                "Respaldos", exc, parent=self,
                contexto="abrir carpeta de respaldos",
                mensaje="No se pudo abrir la carpeta de respaldos en el "
                        "explorador de Windows.")

    def _restaurar_respaldo(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR restaura respaldos.",
                                 parent=self)
            return
        carpeta = db.dir_respaldos()
        os.makedirs(carpeta, exist_ok=True)
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Elegir el respaldo a restaurar",
            initialdir=carpeta,
            filetypes=[("Base de datos de respaldo", "*.db"), ("Todos", "*.*")],
        )
        if not ruta:
            return
        if not messagebox.askyesno(
            "Restaurar respaldo",
            f"Se reemplazará la base de datos ACTUAL por:\n\n"
            f"{os.path.basename(ruta)}\n\n"
            "Lo que se haya cargado después de ese respaldo se perderá.\n"
            "Se generará primero un respaldo de seguridad de la base actual.\n\n"
            "¿Continuar?", parent=self):
            return
        try:
            db.respaldar("antes de restaurar")
            shutil.copy2(ruta, db.DB_PATH)
        except Exception as exc:
            errores.mostrar(
                "Restaurar", exc, parent=self, contexto="restaurar respaldo",
                mensaje="No se pudo restaurar el respaldo.\n"
                        "La base de datos actual no se tocó.")
            return
        db.log_actividad("Respaldo restaurado", os.path.basename(ruta))
        messagebox.showinfo(
            "Restauración correcta",
            "La base de datos fue restaurada.\n\nCerrá y volvé a abrir el "
            "programa para que los cambios tomen efecto.", parent=self)

    # ------------------------------------------------------------- acciones
    def _seleccionar(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        producto = db.producto_por_id(int(sel[0]))
        if producto:
            self.var_nombre.set(producto["nombre"])
            self.var_precio.set(money(producto["precio"]).replace("$", ""))

    def _guardar_producto(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR modifica los productos.",
                                 parent=self)
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Productos",
                                   "Seleccioná un producto de la lista.",
                                   parent=self)
            return
        nombre = self.var_nombre.get().strip()
        precio = parse_numero(self.var_precio.get())
        if not nombre:
            messagebox.showwarning("Productos", "Ingresá el nombre del producto.",
                                   parent=self)
            return
        if precio is None or precio < 0:
            messagebox.showwarning("Productos", "Ingresá un precio válido.",
                                   parent=self)
            return
        db.actualizar_producto(int(sel[0]), nombre, precio)
        messagebox.showinfo("Productos", "Producto actualizado correctamente.",
                            parent=self)
        self.app.refrescar_todo()

    def _nuevo_producto(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR crea productos.",
                                 parent=self)
            return
        nombre = self.var_nombre.get().strip()
        precio = parse_numero(self.var_precio.get())
        if not nombre:
            messagebox.showwarning("Productos", "Ingresá el nombre del producto.",
                                   parent=self)
            return
        if precio is None or precio < 0:
            messagebox.showwarning("Productos", "Ingresá un precio válido.",
                                   parent=self)
            return
        db.crear_producto(nombre, precio)
        self.var_nombre.set("")
        self.var_precio.set("")
        messagebox.showinfo("Productos", "Producto creado correctamente.",
                            parent=self)
        self.app.refrescar_todo()

    def _eliminar_producto(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR elimina productos.",
                                 parent=self)
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Productos",
                                   "Seleccioná un producto de la lista.",
                                   parent=self)
            return
        producto = db.producto_por_id(int(sel[0]))
        if not messagebox.askyesno(
            "Eliminar producto",
            f"¿Eliminar «{producto['nombre']}»?\n"
            "Dejará de estar disponible en el registro de ventas "
            "(las ventas ya registradas se conservan).",
            parent=self,
        ):
            return
        db.eliminar_producto(int(sel[0]))
        self.app.refrescar_todo()

    def _guardar_fondo(self):
        if not db.puede("configuracion"):
            messagebox.showerror("Sin permisos",
                                 "Solo un DESARROLLADOR modifica el fondo inicial.",
                                 parent=self)
            return
        valor = parse_numero(self.var_fondo.get())
        if valor is None or valor < 0:
            messagebox.showwarning("Caja", "Ingresá un monto válido.", parent=self)
            return
        db.set_fondo_inicial(valor)
        messagebox.showinfo("Caja", "Fondo inicial guardado correctamente.",
                            parent=self)
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
    def refresh(self):
        self._aplicar_permisos()
        if not db.puede("configuracion"):
            return
        self._refrescar_respaldo()
        self.tree.delete(*self.tree.get_children())
        for p in db.productos():
            self.tree.insert("", "end", iid=str(p["id"]),
                             values=(p["nombre"], money(p["precio"])))
        self.var_fondo.set(money(db.get_fondo_inicial()).replace("$", ""))
