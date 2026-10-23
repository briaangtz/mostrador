# -*- coding: utf-8 -*-
"""
Sistema de control diario de ventas de garrafas y cierre de caja.
Diseño "Caja del Día" para GARRAFAS — Distribuidora de garrafas.

Requisitos de inicio de sesión (usuario + contraseña) y aplica los permisos
del rango del usuario conectado.

Ejecutar con:  python main.py
"""

import tkinter as tk
from tkinter import messagebox

import database as db
import estilos as st
from util import fecha_corta
from version import VERSION
from ui_login import pedir_login
from ui_inicio import InicioPanel
from ui_ventas import VentasPanel
from ui_estadisticas import EstadisticasPanel
from ui_config import ConfigPanel
from ui_historial import HistorialPanel
from ui_rendicion import RendicionPanel
from ui_admin import AdminPanel
from ui_cuenta import CuentaPanel
from ui_ayuda import SoporteVentana

# (clave, etiqueta del botón, permiso requerido o None)
NAV = [
    ("inicio", "Inicio", None),
    ("ventas", "Ventas", "ventas"),
    ("stats", "Estadísticas y reportes", "estadisticas"),
    ("config", "Configuración", None),
    ("historial", "Historial de cierres", "historial"),
    ("rendicion", "Planilla de rendición", "rendicion"),
    ("admin", "Panel de control", "panel_admin"),
    ("cuenta", "Mi cuenta", None),
]

ANCHO_SIDEBAR = 312
ALTO_BARRA_SUPERIOR = 76


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init()

        self.title(f"GARRAFAS — Control de caja diaria  ·  v{VERSION}")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(1400, int(sw * 0.95))
        alto = min(900, int(sh * 0.92))
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2 - 10)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(1100, ancho), min(700, alto))
        self.configure(bg=st.FONDO)
        self.cancelado = False

        st.aplicar_estilo(self)

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        # ---------------- Inicio de sesión obligatorio ----------------
        self.withdraw()
        usuario = db.usuario_sesion()
        while usuario is None:
            usuario = pedir_login(self)
            if usuario is None:
                self.cancelado = True
                self.destroy()
                return
        self.deiconify()
        self.title(f"GARRAFAS — {usuario['usuario']} "
                   f"({usuario['rango']})  ·  v{VERSION}")

        if db.respaldo_automatico_activo():
            db.respaldar_si_toca("apertura del programa")

        self.caja_fecha = db.hoy()
        self.caja_manual = False
        db.asegurar_caja(self.caja_fecha)
        self.panel_actual = None

        self._construir()

        self.bind_all("<MouseWheel>", self._rueda_global)

        self.after(60000, self._chequear_dia)

        self.mostrar("inicio")
        self.refrescar_todo()

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
        # ---------------- Barra superior (solo contenido, a derecha de sidebar) ----------------
        self.barra_superior = tk.Frame(self, bg=st.BARRA_SUPERIOR, height=ALTO_BARRA_SUPERIOR)
        self.barra_superior.pack(side="top", fill="x")
        self.barra_superior.pack_propagate(False)

        # Fecha + calendario (a la derecha)
        self.lbl_fecha_barra = tk.Label(
            self.barra_superior, text="Jueves, 22 de Octubre de 2026",
            bg=st.BARRA_SUPERIOR, fg=st.BLANCO, font=(st.FUENTE, 11, "bold"))
        self.lbl_fecha_barra.pack(side="right", padx=(0, 16), pady=0)

        # Selector de caja "Caja N° 001"
        self.lbl_caja_selector = tk.Label(
            self.barra_superior, text="Caja N° 001  ▾",
            bg="#1E3A5F", fg=st.BLANCO, font=(st.FUENTE, 11, "bold"),
            padx=14, pady=6, cursor="hand2")
        self.lbl_caja_selector.pack(side="right", padx=(0, 12), pady=(ALTO_BARRA_SUPERIOR // 2 - 14, 0))
        self.lbl_caja_selector.bind("<Button-1>", lambda e: self._abrir_selector_caja())

        # Píldora verde "Abierta"
        self.pill_abierta = tk.Label(
            self.barra_superior, text="●  Abierta",
            bg=st.VERDE, fg=st.BLANCO, font=(st.FUENTE, 11, "bold"),
            padx=14, pady=6, cursor="hand2")
        self.pill_abierta.pack(side="right", padx=(0, 12), pady=(ALTO_BARRA_SUPERIOR // 2 - 14, 0))

        # ---------------- Contenedor principal (sidebar + contenido) ----------------
        self.contenedor_principal = tk.Frame(self, bg=st.FONDO)
        self.contenedor_principal.pack(side="top", fill="both", expand=True)

        # Sidebar fija izquierda
        sidebar = tk.Frame(self.contenedor_principal, bg=st.BARRA, width=ANCHO_SIDEBAR)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Cabecera de la sidebar
        marca = tk.Frame(sidebar, bg=st.BARRA)
        marca.pack(fill="x", padx=20, pady=(24, 20))

        # Icono de garrafa (dibujado en Canvas)
        self.lbl_icono_marca = self._crear_icono_garrafa(marca, tam=40)
        self.lbl_icono_marca.pack(side="left", padx=(0, 12))

        col_texto = tk.Frame(marca, bg=st.BARRA)
        col_texto.pack(side="left", fill="y")
        tk.Label(col_texto, text="GARRAFAS", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 20, "bold")).pack(anchor="w")
        tk.Label(col_texto, text="Control de caja diaria", bg=st.BARRA,
                 fg="#9fb0cc", font=(st.FUENTE, 11)).pack(anchor="w", pady=(2, 0))

        self.ventana_soporte = None

        # ---------------- Menú de navegación ----------------
        self.botones_nav = {}
        for clave, texto, _permiso in NAV:
            b = self._boton_nav(sidebar, texto, clave)
            b.pack(fill="x", padx=12, pady=(0, 6))
        self._actualizar_nav()

        # ---------------- Tarjeta de usuario (anclada abajo) ----------------
        pie = tk.Frame(sidebar, bg=st.BARRA)
        pie.pack(side="bottom", fill="x", padx=16, pady=16)

        separador = tk.Frame(pie, bg="#1E3A5F", height=1)
        separador.pack(fill="x", pady=(0, 12))

        fila_usuario = tk.Frame(pie, bg=st.BARRA)
        fila_usuario.pack(fill="x")

        # Avatar (dibujado en Canvas: círculo con silueta de usuario)
        self._foto_nav_ref = None
        self.canvas_avatar = tk.Canvas(
            fila_usuario, width=44, height=44, bg="#1E3A5F",
            highlightthickness=0, bd=0)
        self.canvas_avatar.pack(side="left", padx=(0, 10))
        self._dibujar_avatar(self.canvas_avatar)

        col_usuario = tk.Frame(fila_usuario, bg=st.BARRA)
        col_usuario.pack(side="left", fill="x", expand=True)

        self._usuario_nav_texto = None
        self._item_usuario = None
        self._anim_usu_id = None
        marco_usuario = tk.Frame(col_usuario, bg=st.BARRA, height=44)
        marco_usuario.pack(fill="x")
        marco_usuario.pack_propagate(False)
        self.canvas_usuario_nav = tk.Canvas(marco_usuario, bg=st.BARRA,
                                            highlightthickness=0, height=44)
        self.canvas_usuario_nav.pack(fill="both", expand=True)
        self.canvas_usuario_nav.bind(
            "<Configure>", lambda e: self._ajustar_texto_usuario())

        btnSalir = tk.Button(
            col_usuario, text="Cerrar sesión",
            command=self.cerrar_sesion,
            relief="flat", bg="#1E3A5F", fg="#f3b4b4",
            font=(st.FUENTE, 9, "bold"), padx=8, pady=4,
            cursor="hand2")
        btnSalir.pack(anchor="w", pady=(8, 0))

        self.lbl_pie_nav = tk.Label(pie, text="", bg=st.BARRA, fg="#9fb0cc",
                                    font=(st.FUENTE, 9), justify="left")
        self.lbl_pie_nav.pack(anchor="w", pady=(8, 0))

        # Botón flotante de soporte
        self.btn_soporte = tk.Button(
            sidebar, text="?", relief="flat", bd=0, bg=st.ACENTO, fg="#ffffff",
            activebackground=st.ACENTO_OSCURO, activeforeground="#ffffff",
            font=(st.FUENTE, 15, "bold"), cursor="hand2",
            width=2, height=1,
            command=self.abrir_soporte)
        self.btn_soporte.pack(side="bottom", anchor="e", padx=12, pady=12)

        # Contenedor de paneles (área de contenido)
        self.contenedor = tk.Frame(self.contenedor_principal, bg=st.FONDO)
        self.contenedor.pack(side="left", fill="both", expand=True)

        self.paneles = {
            "inicio": InicioPanel(self.contenedor, self),
            "ventas": VentasPanel(self.contenedor, self),
            "stats": EstadisticasPanel(self.contenedor, self),
            "config": ConfigPanel(self.contenedor, self),
            "historial": HistorialPanel(self.contenedor, self),
            "rendicion": RendicionPanel(self.contenedor, self),
            "admin": AdminPanel(self.contenedor, self),
            "cuenta": CuentaPanel(self.contenedor, self),
        }
        for panel in self.paneles.values():
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ------------------------------------------------------------------ Helpers UI
    def _crear_icono_garrafa(self, parent, tam=40):
        """Dibuja un icono de garrafa en un Canvas."""
        canvas = tk.Canvas(parent, width=tam, height=tam,
                           bg=st.BARRA, highlightthickness=0, bd=0)
        cx = cy = tam // 2
        r = tam // 2 - 2
        # Cuerpo de la garrafa (trapecio simplificado)
        st._linea(canvas, cx - 14, cy + 10, cx + 14, cy + 10, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx - 10, cy + 10, cx - 16, cy - 6, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx + 10, cy + 10, cx + 16, cy - 6, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx - 16, cy - 6, cx + 16, cy - 6, st.BLANCO, 3, ("g",))
        # Tapa
        st._linea(canvas, cx - 8, cy - 6, cx + 8, cy - 6, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx - 8, cy - 6, cx - 8, cy - 14, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx + 8, cy - 6, cx + 8, cy - 14, st.BLANCO, 3, ("g",))
        st._linea(canvas, cx - 8, cy - 14, cx + 8, cy - 14, st.BLANCO, 3, ("g",))
        return canvas

    def _dibujar_avatar(self, canvas):
        """Dibuja un avatar genérico de usuario en el Canvas."""
        w = h = 44
        cx, cy = w // 2, h // 2
        r = 16
        st._circulo(canvas, cx, cy, r, fill="#334155", outline="", tags=("avatar",))
        # Cabeza
        st._circulo(canvas, cx, cy - 10, 8, fill="#94a3b8", outline="", tags=("avatar",))
        # Hombros
        st._linea(canvas, cx - 14, cy + 4, cx + 14, cy + 4, "#94a3b8", 3, ("avatar",))

    def _boton_nav(self, parent, texto, clave):
        """Botón de navegación con fondo transparente, cambia al activarse."""
        b = tk.Button(
            parent, text=texto, anchor="w", relief="flat", bd=0,
            bg=st.BARRA, fg="#c7d2e4", font=(st.FUENTE, 11, "bold"),
            padx=20, pady=0, cursor="hand2",
            command=lambda k=clave: self.mostrar(k),
        )
        b.bind("<Enter>", lambda e, btn=b: btn.config(bg="#1E4FD8"))
        b.bind("<Leave>", lambda e, btn=b: btn.config(
            bg=st.ACENTO_OSCURO if getattr(btn, "activo", False) else st.BARRA))
        self.botones_nav[clave] = b
        return b

    def _abrir_selector_caja(self):
        """Muestra un menú desplegable para seleccionar una caja anterior."""
        cajas = db.todas_las_cajas()
        if not cajas:
            return
        
        # Crear menú popup
        menu = tk.Menu(self, tearoff=0, bg=st.FONDO, fg=st.TEXTO,
                       font=(st.FUENTE, 10), activebackground=st.ACENTO,
                       activeforeground=st.BLANCO, borderwidth=1,
                       relief="solid")
        
        for c in cajas:
            estado = "✓ cerrada" if c["estado"] == "cerrada" else "• abierta"
            fecha_str = db.fecha_larga(c["fecha"])
            label = f"{fecha_str}  ({estado})"
            # Usar lambda con default para capturar la fecha correcta
            menu.add_command(
                label=label,
                command=lambda f=c["fecha"]: self.cambiar_caja(f)
            )
        
        # Mostrar menú bajo el label
        x = self.lbl_caja_selector.winfo_rootx()
        y = self.lbl_caja_selector.winfo_rooty() + self.lbl_caja_selector.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------ Nav
    def abrir_soporte(self):
        v = self.ventana_soporte
        if v is not None:
            try:
                if v.winfo_exists():
                    v.mostrar()
                    return
            except tk.TclError:
                pass
        self.ventana_soporte = SoporteVentana(self, boton=self.btn_soporte)

    def _actualizar_nav(self):
        for clave, _texto, permiso in NAV:
            b = self.botones_nav[clave]
            if permiso is None or db.puede(permiso):
                b.pack(fill="x", padx=12, pady=(0, 6))
            else:
                b.pack_forget()

    def mostrar(self, clave):
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
                b.config(bg=st.ACENTO_OSCURO if activo else st.BARRA,
                         fg="#ffffff" if activo else "#c7d2e4")
        panel.refresh()
        self._actualizar_pie()
        if self._usuario_nav_texto:
            self._animar_entrada_usuario()

    # ---------------------------------------------------------- sesión
    def _al_cerrar(self):
        try:
            if db.respaldo_automatico_activo():
                db.respaldar_si_toca("cierre del programa")
            db.cerrar_sesion()
        except Exception:
            pass
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
        self.title(f"GARRAFAS — {usuario['usuario']} "
                   f"({usuario['rango']})  ·  v{VERSION}")
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
        self.caja_manual = fecha != db.hoy()
        db.asegurar_caja(fecha)
        self._actualizar_selector_caja(fecha)
        self.refrescar_todo()

    def _actualizar_selector_caja(self, fecha):
        """Actualiza el texto del selector de caja en la barra superior y en el panel inicio."""
        estado = "abierta" if self.caja_actual()["estado"] == "abierta" else "cerrada"
        texto = f"{fecha_corta(fecha)} (r. {estado})"
        # Actualizar selector en barra superior
        self.lbl_caja_selector.config(text=f"Caja N° {fecha[-2:]}  ▾")
        # Actualizar selector en panel inicio si está visible
        if "inicio" in self.paneles:
            inicio = self.paneles["inicio"]
            if hasattr(inicio, 'actualizar_selector_caja'):
                inicio.actualizar_selector_caja(texto)

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
        delta = int(-evento.delta / 120)
        if not delta:
            return
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
        c = self.canvas_usuario_nav
        if self._item_usuario is None:
            self._item_usuario = c.create_text(
                0, self._y_texto_usuario(), anchor="w", justify="left",
                text=texto, fill="#ffffff",
                font=(st.FUENTE, 10, "bold"),
            )
        else:
            c.itemconfig(self._item_usuario, text=texto)
        c.coords(self._item_usuario, 0, self._y_texto_usuario())
        self._ajustar_texto_usuario()

    def _y_texto_usuario(self):
        return max(1, self.canvas_usuario_nav.winfo_height() // 2)

    def _ajustar_texto_usuario(self):
        if self._item_usuario is None:
            return
        c = self.canvas_usuario_nav
        ancho = c.winfo_width()
        if ancho > 20:
            c.itemconfig(self._item_usuario, width=max(20, ancho - 6))

    def _animar_entrada_usuario(self):
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
            self._anim_usu_id = self.after(80, self._animar_entrada_usuario)
            return
        pasos = 10
        estado = {"i": 0}

        def paso():
            self._anim_usu_id = None
            i = estado["i"]
            t = i / (pasos - 1)
            suave = 1 - (1 - t) ** 2
            x = int(ancho * (1 - suave))
            self.canvas_usuario_nav.coords(
                self._item_usuario, x, self._y_texto_usuario())
            estado["i"] += 1
            if estado["i"] < pasos:
                self._anim_usu_id = self.after(22, paso)
            else:
                self.canvas_usuario_nav.coords(
                    self._item_usuario, 0, self._y_texto_usuario())

        paso()

    def _actualizar_foto_nav(self):
        ruta = db.foto_perfil()
        if not ruta:
            self.canvas_avatar.delete("all")
            self._dibujar_avatar(self.canvas_avatar)
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
            img = img.resize((44, 44), Image.LANCZOS)
            foto = ImageTk.PhotoImage(img)
            self._foto_nav_ref = foto
            self._foto_nav_cache = clave
            self.canvas_avatar.delete("all")
            self.canvas_avatar.create_image(22, 22, image=foto, tags=("foto",))
        except Exception:
            self.canvas_avatar.delete("all")
            self._dibujar_avatar(self.canvas_avatar)
            self._foto_nav_ref = None

    def _chequear_dia(self):
        hoy = db.hoy()
        if hoy != self.caja_fecha:
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
