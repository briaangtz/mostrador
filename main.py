# -*- coding: utf-8 -*-
"""
Sistema de control diario de ventas de garrafas y cierre de caja.

Requiere inicio de sesión (usuario + contraseña) y aplica los permisos
del rango del usuario conectado.

Ejecutar con:  python main.py
"""

import tkinter as tk
from tkinter import messagebox

import database as db
import estilos as st
from util import ruta_recurso
from ui_login import pedir_login
from ui_inicio import InicioPanel
from ui_ventas import VentasPanel
from ui_estadisticas import EstadisticasPanel
from ui_config import ConfigPanel
from ui_historial import HistorialPanel
from ui_admin import AdminPanel
from ui_cuenta import CuentaPanel

# (clave, etiqueta del botón, permiso requerido o None)
NAV = [
    ("inicio", "Inicio\nCaja del día", None),
    ("ventas", "Ventas\nRegistro del día", "ventas"),
    ("stats", "Estadísticas\nVentas y reportes", "estadisticas"),
    ("config", "Configuración\nPrecios y seguridad", None),
    ("historial", "Historial\nde cierres", "historial"),
    ("admin", "Administración\nUsuarios y actividad", "panel_admin"),
    ("cuenta", "Mi cuenta\nPerfil y seguridad", None),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init()

        self.title("Control de Ventas de Garrafas — Caja Diaria")
        # Ventana adaptada al tamaño de pantalla (chica o grande), centrada
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(1200, int(sw * 0.95))
        alto = min(760, int(sh * 0.9))
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2 - 20)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(960, ancho), min(600, alto))
        self.configure(bg=st.FONDO)
        self.cancelado = False

        # Ícono del programa (icono.ico, si existe)
        try:
            self.iconbitmap(ruta_recurso("icono.ico"))
        except Exception:
            pass

        st.aplicar_estilo(self)

        # Al cerrar la ventana: último respaldo del día y cierre de sesión
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        # ---------------- Inicio de sesión obligatorio ----------------
        self.withdraw()
        usuario = db.usuario_sesion()
        while usuario is None:
            usuario = pedir_login(self)
            if usuario is None:
                # Canceló o cerró la ventana de login: no se entra al sistema
                self.cancelado = True
                self.destroy()
                return
        self.deiconify()
        self.title(f"Control de Ventas de Garrafas — {usuario['usuario']} "
                   f"({usuario['rango']})")

        # Respaldo automático: uno por día al abrir el programa
        if db.respaldo_automatico_activo():
            db.respaldar_si_toca("apertura del programa")

        self.caja_fecha = db.hoy()
        self.caja_manual = False   # True si el usuario eligió otra fecha a mano
        db.asegurar_caja(self.caja_fecha)
        self.panel_actual = None

        self._construir()

        # Rueda del mouse: hace scroll en el panel o diálogo que corresponda
        self.bind_all("<MouseWheel>", self._rueda_global)

        # Crea la caja del día si se cruzó la medianoche con el programa abierto
        self.after(60000, self._chequear_dia)

        self.mostrar("inicio")
        self.refrescar_todo()

        # Aviso si quedó alguna caja sin cerrar
        pendientes = [c for c in db.cajas_abiertas() if c["fecha"] != self.caja_fecha]
        if pendientes:
            fechas = ", ".join(db.fecha_larga(c["fecha"]) for c in pendientes)
            self.after(400, lambda: messagebox.showwarning(
                "Cajas sin cerrar",
                f"Quedaron cajas sin cerrar de: {fechas}.\n\n"
                "Podés abrirlas desde Inicio o desde Historial de cierres.",
                parent=self,
            ))

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # Barra lateral
        sidebar = tk.Frame(self, bg=st.BARRA, width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        marca = tk.Frame(sidebar, bg=st.BARRA)
        marca.pack(fill="x", padx=16, pady=(22, 24))
        tk.Label(marca, text="GARRAFAS", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 18, "bold")).pack(anchor="w")
        tk.Label(marca, text="Control de caja diaria", bg=st.BARRA,
                 fg="#9fb0cc", font=(st.FUENTE, 9)).pack(anchor="w")

        self.botones_nav = {}
        for clave, texto, _permiso in NAV:
            b = tk.Button(
                sidebar, text=texto, anchor="w", relief="flat", bd=0,
                bg=st.BARRA, fg="#c7d2e4", font=(st.FUENTE, 10, "bold"),
                padx=18, pady=12, cursor="hand2",
                command=lambda k=clave: self.mostrar(k),
            )
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg="#22304d"))
            b.bind("<Leave>", lambda e, btn=b: btn.config(
                bg=st.ACENTO if getattr(btn, "activo", False) else st.BARRA))
            self.botones_nav[clave] = b
        self._actualizar_nav()

        pie = tk.Frame(sidebar, bg=st.BARRA)
        pie.pack(side="bottom", fill="x", padx=16, pady=14)

        fila_usuario = tk.Frame(pie, bg=st.BARRA)
        fila_usuario.pack(fill="x")

        # Foto de perfil (elegida desde Mi cuenta)
        self._foto_nav_ref = None
        self.lbl_foto_nav = tk.Label(fila_usuario, text="👤", bg="#1e293b",
                                     fg="#9fb0cc", font=(st.FUENTE, 18),
                                     width=5, height=3)
        self.lbl_foto_nav.pack(side="left", padx=(0, 10))

        col_usuario = tk.Frame(fila_usuario, bg=st.BARRA)
        col_usuario.pack(side="left", fill="x", expand=True)

        # Usuario conectado: texto con efecto de entrada deslizante
        # (el Canvas recorta el texto mientras se desliza)
        self._usuario_nav_texto = None
        self._item_usuario = None
        self._anim_usu_id = None
        marco_usuario = tk.Frame(col_usuario, bg=st.BARRA, height=38)
        marco_usuario.pack(fill="x")
        marco_usuario.pack_propagate(False)
        self.canvas_usuario_nav = tk.Canvas(marco_usuario, bg=st.BARRA,
                                            highlightthickness=0, height=38)
        self.canvas_usuario_nav.pack(fill="both", expand=True)

        btnSalir = tk.Button(col_usuario, text="Cerrar sesión",
                             command=self.cerrar_sesion,
                             relief="flat", bg="#3b4a6b", fg="#f3b4b4",
                             font=(st.FUENTE, 9, "bold"), padx=8, pady=5,
                             cursor="hand2")
        btnSalir.pack(anchor="w", pady=(6, 8))

        self.lbl_pie_nav = tk.Label(pie, text="", bg=st.BARRA, fg="#9fb0cc",
                                    font=(st.FUENTE, 9), justify="left")
        self.lbl_pie_nav.pack(anchor="w")

        # Contenedor de paneles
        contenedor = tk.Frame(self, bg=st.FONDO)
        contenedor.pack(side="left", fill="both", expand=True)

        self.paneles = {
            "inicio": InicioPanel(contenedor, self),
            "ventas": VentasPanel(contenedor, self),
            "stats": EstadisticasPanel(contenedor, self),
            "config": ConfigPanel(contenedor, self),
            "historial": HistorialPanel(contenedor, self),
            "admin": AdminPanel(contenedor, self),
            "cuenta": CuentaPanel(contenedor, self),
        }
        for panel in self.paneles.values():
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _actualizar_nav(self):
        """Muestra/oculta los botones según los permisos de la sesión."""
        for clave, _texto, permiso in NAV:
            b = self.botones_nav[clave]
            if permiso is None or db.puede(permiso):
                b.pack(fill="x")
            else:
                b.pack_forget()

    def mostrar(self, clave):
        # Validación interna: aunque el botón esté oculto, no se entra sin permiso
        permiso = dict((k, p) for k, _t, p in NAV).get(clave)
        if permiso and not db.puede(permiso):
            messagebox.showwarning(
                "Sin permisos",
                "Tu usuario no tiene acceso a esta sección.", parent=self)
            return
        panel = self.paneles[clave]
        panel.lift()
        self.panel_actual = clave
        for k, b in self.botones_nav.items():
            activo = k == clave
            b.activo = activo
            if b.winfo_ismapped():
                b.config(bg=st.ACENTO if activo else st.BARRA,
                         fg="#ffffff" if activo else "#c7d2e4")
        panel.refresh()
        self._actualizar_pie()
        # Efecto de entrada del usuario/rango al cambiar de pantalla
        if self._usuario_nav_texto:
            self._animar_entrada_usuario()

    # ---------------------------------------------------------- sesión
    def _al_cerrar(self):
        """Al salir: respaldo del día (si falta) y cierre de sesión."""
        try:
            if db.respaldo_automatico_activo():
                db.respaldar_si_toca("cierre del programa")
            db.cerrar_sesion()
        except Exception:
            pass                      # nunca impedir que se cierre la ventana
        self.destroy()

    def cerrar_sesion(self):
        if not messagebox.askyesno("Cerrar sesión",
                                   "¿Cerrar la sesión actual y volver al "
                                   "inicio de sesión?", parent=self):
            return
        db.cerrar_sesion()
        self.withdraw()
        while True:
            usuario = pedir_login(self)
            if usuario is None:
                self.cancelado = True
                self.destroy()
                return
            break
        # El rango puede haber cambiado: se actualiza la navegación
        self.title(f"Control de Ventas de Garrafas — {usuario['usuario']} "
                   f"({usuario['rango']})")
        self._actualizar_nav()
        if self.panel_actual and not self.botones_nav[self.panel_actual].winfo_ismapped():
            self.panel_actual = None
            self.mostrar("inicio")
        self.deiconify()
        self.refrescar_todo()

    # --------------------------------------------------------------- datos
    def caja_actual(self):
        return db.asegurar_caja(self.caja_fecha)

    def cambiar_caja(self, fecha):
        self.caja_fecha = fecha
        # Si eligió una fecha que no es la de hoy, es una elección manual:
        # el chequeo de medianoche no debe sacarlo de esa caja.
        self.caja_manual = fecha != db.hoy()
        db.asegurar_caja(fecha)
        self.refrescar_todo()

    def refrescar_todo(self):
        for panel in self.paneles.values():
            try:
                panel.refresh()
            except tk.TclError:
                pass
        try:
            self._actualizar_pie()
        except tk.TclError:
            pass
        if self.panel_actual:
            self.paneles[self.panel_actual].lift()

    def _rueda_global(self, evento):
        """
        Rueda del mouse: hace scroll en el diálogo abierto si tiene scroll,
        y si no, en el panel de la pantalla actual. Así ningún pantalla se
        queda con contenido oculto en ventanas chicas.
        """
        delta = int(-evento.delta / 120)
        if not delta:
            return
        # 1) Diálogos (el último es el que está visible)
        for hijo in reversed(self.winfo_children()):
            try:
                if hijo.winfo_class() != "Toplevel" or not hijo.winfo_exists():
                    continue
            except tk.TclError:
                continue
            lienzo = getattr(hijo, "canvas_scroll", None)
            if lienzo is not None:
                lienzo.yview_scroll(delta, "units")
                return
        # 2) Panel de la pantalla actual
        panel = self.paneles.get(self.panel_actual)
        lienzo = getattr(panel, "canvas_scroll", None) if panel else None
        if lienzo is not None:
            lienzo.yview_scroll(delta, "units")

    def _actualizar_pie(self):
        u = db.usuario_sesion()
        texto = (f"Usuario: {u['usuario']}\nRango: {u['rango']}" if u else "")
        if texto != self._usuario_nav_texto:
            self._usuario_nav_texto = texto
            self._pintar_usuario_nav(texto)
            if texto:
                self._animar_entrada_usuario()
        self._actualizar_foto_nav()
        caja = self.caja_actual()
        if not caja:
            return
        estado = "ABIERTA" if caja["estado"] == "abierta" else "CERRADA"
        r = db.resumen(caja["id"])
        self.lbl_pie_nav.config(
            text=f"Caja: {db.fecha_larga(caja['fecha'])}\n"
                 f"Estado: {estado}\n"
                 f"Vendido: ${r['total_vendido']:,.0f}".replace(",", ".")
        )

    def _pintar_usuario_nav(self, texto):
        """Escribe (o actualiza) el texto de usuario/rango en el Canvas."""
        c = self.canvas_usuario_nav
        if self._item_usuario is None:
            self._item_usuario = c.create_text(
                0, 19, anchor="w", justify="left", text=texto, fill="#ffffff",
                font=(st.FUENTE, 10, "bold"),
            )
        else:
            c.itemconfig(self._item_usuario, text=texto)
        c.coords(self._item_usuario, 0, 19)

    def _animar_entrada_usuario(self):
        """Efecto: el usuario/rango entra deslizándose desde atrás (derecha)
        hacia adelante (izquierda) y queda fijo al costado."""
        if self._item_usuario is None:
            return
        if self._anim_usu_id is not None:
            try:
                self.after_cancel(self._anim_usu_id)
            except Exception:
                pass
            self._anim_usu_id = None
        ancho = self.canvas_usuario_nav.winfo_width()
        if ancho < 30:
            # Todavía no se maquetó: se reintenta en un instante
            self._anim_usu_id = self.after(80, self._animar_entrada_usuario)
            return
        pasos = 10
        estado = {"i": 0}

        def paso():
            self._anim_usu_id = None
            i = estado["i"]
            t = i / (pasos - 1)
            suave = 1 - (1 - t) ** 2          # ease-out: entra rápido y frena
            x = int(ancho * (1 - suave))
            self.canvas_usuario_nav.coords(self._item_usuario, x, 19)
            estado["i"] += 1
            if estado["i"] < pasos:
                self._anim_usu_id = self.after(22, paso)
            else:
                self.canvas_usuario_nav.coords(self._item_usuario, 0, 19)

        paso()

    def _actualizar_foto_nav(self):
        """Muestra la foto de perfil en el lateral (si el usuario tiene)."""
        ruta = db.foto_perfil()
        if not ruta:
            if self._foto_nav_ref is not None:
                self.lbl_foto_nav.config(image="", text="👤",
                                         width=5, height=3)
                self._foto_nav_ref = None
                self._foto_nav_cache = None
            return
        try:
            import os
            clave = (ruta, os.path.getmtime(ruta))
            if getattr(self, "_foto_nav_cache", None) == clave and self._foto_nav_ref:
                return
            from PIL import Image, ImageTk
            img = Image.open(ruta).convert("RGB")
            w, h = img.size
            lado = min(w, h)
            img = img.crop(((w - lado) // 2, (h - lado) // 2,
                            (w + lado) // 2, (h + lado) // 2))
            img = img.resize((52, 52), Image.LANCZOS)
            foto = ImageTk.PhotoImage(img)
            self._foto_nav_ref = foto
            self._foto_nav_cache = clave
            self.lbl_foto_nav.config(image=foto, text="", width=0, height=0)
        except Exception:
            self.lbl_foto_nav.config(image="", text="👤", width=5, height=3)
            self._foto_nav_ref = None

    def _chequear_dia(self):
        hoy = db.hoy()
        if hoy != self.caja_fecha:
            # La caja del día nuevo se crea siempre (para no mezclar datos),
            # pero si el usuario está viendo otra fecha a propósito,
            # NO se le roba la vista: el banner de Inicio avisa igual.
            db.asegurar_caja(hoy)
            if not self.caja_manual:
                self.caja_fecha = hoy
                self.refrescar_todo()
                messagebox.showinfo(
                    "Nuevo día",
                    f"Se creó automáticamente la caja del {db.fecha_larga(hoy)}.\n"
                    "La caja anterior queda guardada de forma separada.",
                    parent=self,
                )
            else:
                self.refrescar_todo()
        self.after(60000, self._chequear_dia)


def main():
    app = App()
    if getattr(app, "cancelado", False):
        return
    app.mainloop()


if __name__ == "__main__":
    main()
