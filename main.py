# -*- coding: utf-8 -*-
"""
Sistema de control diario de ventas de garrafas y cierre de caja.
Diseño "Caja del Día" para GARRAFAS — Distribuidora de garrafas.

Requisitos de inicio de sesión (usuario + contraseña) y aplica los permisos
del rango del usuario conectado.

Ejecutar con:  python main.py
"""

import datetime
import os
import sys
import tkinter as tk
from tkinter import messagebox

import database as db
import estilos as st
import iconos as ic
from util import fecha_corta
from version import VERSION
from ui_login import pedir_login
from ui_inicio import InicioPanel, _num_caja
from ui_ventas import VentasPanel
from ui_estadisticas import EstadisticasPanel
from ui_config import ConfigPanel
from ui_historial import HistorialPanel
from ui_rendicion import RendicionPanel
from ui_admin import AdminPanel
from ui_cuenta import CuentaPanel
from ui_ayuda import SoporteVentana
from widgets_figma import Tarjeta, ItemNav, Pildora

# (clave, etiqueta, permiso requerido o None, icono, sección del menú)
NAV = [
    ("inicio", "Inicio", None, "home", "OPERACIÓN"),
    ("ventas", "Ventas", "ventas", "cart", "OPERACIÓN"),
    ("stats", "Estadísticas y reportes", "estadisticas", "chart", "OPERACIÓN"),
    ("historial", "Historial de cierres", "historial", "history", "OPERACIÓN"),
    ("rendicion", "Planilla de rendición", "rendicion", "clipboard", "OPERACIÓN"),
    ("admin", "Panel de control", "panel_admin", "grid", "OPERACIÓN"),
    ("config", "Configuración", None, "gear", "ADMINISTRACIÓN"),
    ("cuenta", "Mi cuenta", None, "user", "ADMINISTRACIÓN"),
]
SECCIONES = ("OPERACIÓN", "ADMINISTRACIÓN")

# Texto de las migas de pan ("Inicio › ...") según la pantalla
MIGAS = {"inicio": "Caja del día"}

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

ANCHO_SIDEBAR = 252
ALTO_BARRA_SUPERIOR = 64
BLANCO = "#FFFFFF"


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

        # Icono de la ventana (barra de tareas / título). En el .exe compilado
        # icono.ico queda extraído en sys._MEIPASS.
        try:
            if getattr(sys, "frozen", False):
                ruta_icono = os.path.join(sys._MEIPASS, "icono.ico")
            else:
                ruta_icono = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "icono.ico")
            if os.path.exists(ruta_icono):
                self.iconbitmap(ruta_icono)
        except tk.TclError:
            pass

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
        # Barra lateral a toda la altura; a la derecha: barra superior + paneles
        self.contenedor_principal = tk.Frame(self, bg=st.FONDO)
        self.contenedor_principal.pack(fill="both", expand=True)

        self._construir_sidebar(self.contenedor_principal)

        derecha = tk.Frame(self.contenedor_principal, bg=st.FONDO)
        derecha.pack(side="left", fill="both", expand=True)
        self._construir_barra_superior(derecha)

        # Contenedor de paneles (área de contenido)
        self.contenedor = tk.Frame(derecha, bg=st.FONDO)
        self.contenedor.pack(side="top", fill="both", expand=True)

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

    # ---------------------------------------------------------- barra lateral
    def _construir_sidebar(self, parent):
        SB = st.SIDEBAR
        sidebar = tk.Frame(parent, bg=SB, width=ANCHO_SIDEBAR)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Cabecera: logo (llama sobre cuadro azul) + nombre
        marca = tk.Frame(sidebar, bg=SB)
        marca.pack(side="top", fill="x", padx=18, pady=(18, 8))
        tk.Label(marca, bg=SB, image=ic.cuadro(
            "flame", 42, "#FFFFFF", st.ACENTO, 10, 24, 1.8)
        ).pack(side="left", padx=(0, 12))
        col = tk.Frame(marca, bg=SB)
        col.pack(side="left")
        tk.Label(col, text="GARRAFAS", bg=SB, fg="#FFFFFF",
                 font=(st.FUENTE, 17)).pack(anchor="w")
        tk.Label(col, text="Control de caja diaria", bg=SB, fg="#9FB0CC",
                 font=(st.FUENTE, 9)).pack(anchor="w")

        self.ventana_soporte = None

        # Pie (se empaqueta primero para que siempre tenga lugar abajo)
        pie = tk.Frame(sidebar, bg=SB)
        pie.pack(side="bottom", fill="x", padx=14, pady=(0, 12))

        tarj = Tarjeta(pie, fondo=st.SIDEBAR_TARJETA, sin_borde=True, radio=12,
                       padx=14, pady=10, exterior=SB)
        tarj.pack(fill="x")
        t = tarj.cuerpo
        t.columnconfigure(1, weight=1)
        self.lbl_pie_caja = tk.Label(t, text="Caja: —", bg=st.SIDEBAR_TARJETA,
                                     fg="#C7D2E4", font=(st.FUENTE, 9))
        self.lbl_pie_caja.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        tk.Label(t, text="Estado", bg=st.SIDEBAR_TARJETA, fg="#C7D2E4",
                 font=(st.FUENTE, 9)).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_pie_estado = tk.Label(t, text="", bg=st.SIDEBAR_TARJETA,
                                       fg="#6EE7B7", font=(st.FUENTE, 9, "bold"))
        self.lbl_pie_estado.grid(row=1, column=1, sticky="e", pady=2)
        tk.Label(t, text="Vendido", bg=st.SIDEBAR_TARJETA, fg="#C7D2E4",
                 font=(st.FUENTE, 9)).grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_pie_vendido = tk.Label(t, text="", bg=st.SIDEBAR_TARJETA,
                                        fg="#FFFFFF", font=(st.FUENTE, 9, "bold"))
        self.lbl_pie_vendido.grid(row=2, column=1, sticky="e", pady=2)

        # Usuario: avatar (inicial o foto) + nombre + rango
        fila = tk.Frame(pie, bg=SB)
        fila.pack(fill="x", pady=(12, 0), padx=4)
        self._foto_nav_ref = None
        self._foto_nav_cache = None
        self.canvas_avatar = tk.Canvas(fila, width=44, height=44, bg=SB,
                                       highlightthickness=0, bd=0)
        self.canvas_avatar.pack(side="left", padx=(0, 10))
        col_u = tk.Frame(fila, bg=SB)
        col_u.pack(side="left", fill="x", expand=True)
        self.lbl_usuario_nombre = tk.Label(col_u, text="", bg=SB, fg="#FFFFFF",
                                           font=(st.FUENTE, 11, "bold"), anchor="w")
        self.lbl_usuario_nombre.pack(fill="x")
        self.lbl_usuario_rango = tk.Label(col_u, text="", bg=SB, fg="#A2B0C4",
                                          font=(st.FUENTE, 8), anchor="w")
        self.lbl_usuario_rango.pack(fill="x")

        # Cerrar sesión
        salir = tk.Frame(pie, bg=SB, cursor="hand2")
        salir.pack(fill="x", pady=(8, 0), padx=4)
        ico_salir = tk.Label(salir, bg=SB, cursor="hand2",
                             image=ic.icono("logout", 18, "#A9B7CE", 1.8))
        ico_salir.pack(side="left", padx=(2, 10), pady=4)
        txt_salir = tk.Label(salir, text="Cerrar sesión", bg=SB, fg="#B6C3DA",
                             font=(st.FUENTE, 10), cursor="hand2")
        txt_salir.pack(side="left")
        for w in (salir, ico_salir, txt_salir):
            w.bind("<Button-1>", lambda e: self.cerrar_sesion())
        txt_salir.bind("<Enter>", lambda e: txt_salir.config(fg="#FFFFFF"))
        txt_salir.bind("<Leave>", lambda e: txt_salir.config(fg="#B6C3DA"))

        # Menú de navegación con secciones
        self.nav_frame = tk.Frame(sidebar, bg=SB)
        self.nav_frame.pack(side="top", fill="both", expand=True, pady=(4, 0))
        self.secciones_lbl = {}
        for nombre in SECCIONES:
            self.secciones_lbl[nombre] = tk.Label(
                self.nav_frame, text=nombre, bg=SB, fg="#A2B0C4",
                font=(st.FUENTE, 8, "bold"), anchor="w")
        self.botones_nav = {}
        for clave, texto, _permiso, icono, _sec in NAV:
            self.botones_nav[clave] = ItemNav(
                self.nav_frame, texto, icono,
                lambda k=clave: self.mostrar(k))
        self._actualizar_nav()

    # ---------------------------------------------------------- barra superior
    def _construir_barra_superior(self, parent):
        barra = tk.Frame(parent, bg=BLANCO, height=ALTO_BARRA_SUPERIOR)
        barra.pack(side="top", fill="x")
        barra.pack_propagate(False)
        self.barra_superior = barra
        tk.Frame(parent, bg=st.BARRA_BORDE, height=1).pack(side="top", fill="x")

        # --- derecha (se empaqueta de derecha a izquierda) ---
        # Botón de ayuda
        self.btn_soporte = tk.Label(
            barra, bg=BLANCO, cursor="hand2",
            image=ic.avatar("?", 30, st.ACENTO, "#FFFFFF", 0.58))
        self.btn_soporte.pack(side="right", padx=(6, 24))
        self.btn_soporte.bind("<Button-1>", lambda e: self.abrir_soporte())
        self.btn_soporte.bind("<Enter>", lambda e: self.btn_soporte.config(
            image=ic.avatar("?", 30, st.ACENTO_OSCURO, "#FFFFFF", 0.58)))
        self.btn_soporte.bind("<Leave>", lambda e: self.btn_soporte.config(
            image=ic.avatar("?", 30, st.ACENTO, "#FFFFFF", 0.58)))

        # Píldora de estado
        self.pill_abierta = Pildora(barra, "Abierta", "#ECF8F1", st.VERDE_OSCURO,
                                    exterior=BLANCO)
        self.pill_abierta.pack(side="right", padx=(0, 12))

        # Selector "Caja N° 001"
        self.lbl_caja_selector = Tarjeta(barra, radio=8, padx=12, pady=7,
                                         borde="#D9E0EC", ancho=150,
                                         exterior=BLANCO)
        self.lbl_caja_selector.pack(side="right", padx=(0, 12))
        cs = self.lbl_caja_selector.cuerpo
        flecha = tk.Label(cs, bg=st.TARJETA,
                          image=ic.icono("chevron", 16, st.TEXTO_SUAVE))
        flecha.pack(side="right")
        self.lbl_caja_texto = tk.Label(cs, text="Caja N° 001", bg=st.TARJETA,
                                       fg=st.TEXTO, font=(st.FUENTE, 10, "bold"))
        self.lbl_caja_texto.pack(side="left")
        for w in (self.lbl_caja_selector, cs, flecha, self.lbl_caja_texto):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", lambda e: self._abrir_selector_caja())

        # Fecha con calendario
        self.lbl_fecha_barra = tk.Label(barra, text="", bg=BLANCO,
                                        fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10))
        self.lbl_fecha_barra.pack(side="right", padx=(0, 18))
        tk.Label(barra, bg=BLANCO,
                 image=ic.icono("calendar", 20, st.TEXTO_SUAVE, 1.7)
                 ).pack(side="right", padx=(0, 8))

        # --- izquierda: migas de pan ---
        self.lbl_miga_inicio = tk.Label(barra, text="Inicio", bg=BLANCO,
                                        fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10),
                                        cursor="hand2")
        self.lbl_miga_inicio.pack(side="left", padx=(28, 6))
        self.lbl_miga_inicio.bind("<Button-1>", lambda e: self.mostrar("inicio"))
        tk.Label(barra, bg=BLANCO,
                 image=ic.icono("chevron_right", 16, st.TEXTO_SUAVE, 1.7)
                 ).pack(side="left", padx=(0, 6))
        self.lbl_miga_actual = tk.Label(barra, text="Caja del día", bg=BLANCO,
                                        fg=st.TEXTO, font=(st.FUENTE, 10, "bold"))
        self.lbl_miga_actual.pack(side="left")

    def _fecha_barra(self, fecha):
        try:
            d = datetime.date.fromisoformat(str(fecha)[:10])
            return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"
        except Exception:
            return fecha_corta(fecha)

    def _actualizar_barra(self):
        """Fecha, número de caja, píldora de estado y migas de pan."""
        caja = self.caja_actual()
        if caja:
            self.lbl_fecha_barra.config(text=self._fecha_barra(caja["fecha"]))
            n = _num_caja(caja)
            self.lbl_caja_texto.config(text=f"Caja N° {n}" if n else "Caja")
            if caja["estado"] == "abierta":
                self.pill_abierta.set("Abierta", "#ECF8F1", st.VERDE_OSCURO)
            else:
                self.pill_abierta.set("Cerrada", "#FDEEEE", st.ROJO)
        clave = self.panel_actual or "inicio"
        nombre = MIGAS.get(clave) or next(
            (t for k, t, _p, _i, _s in NAV if k == clave), "")
        self.lbl_miga_actual.config(text=nombre)

    # ------------------------------------------------------------------ Helpers UI
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
        """Muestra solo lo que el usuario puede ver, con sus secciones."""
        for w in self.nav_frame.winfo_children():
            w.pack_forget()
        primera = True
        for nombre in SECCIONES:
            claves = [c for c, _t, p, _i, s in NAV
                      if s == nombre and (p is None or db.puede(p))]
            if not claves:
                continue
            self.secciones_lbl[nombre].pack(
                fill="x", padx=22, pady=(10 if primera else 18, 6))
            primera = False
            for c in claves:
                self.botones_nav[c].pack(fill="x", padx=14, pady=2)

    def mostrar(self, clave):
        permiso = dict((k, p) for k, _t, p, _i, _s in NAV).get(clave)
        if permiso and not db.puede(permiso):
            messagebox.showwarning(
                "Sin permisos",
                "Tu usuario no tiene acceso a esta sección.", parent=self)
            return
        panel = self.paneles[clave]
        panel.lift()
        self.panel_actual = clave
        for k, b in self.botones_nav.items():
            b.set_activo(k == clave)
        self._actualizar_barra()
        panel.refresh()
        self._actualizar_pie()

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
        """Actualiza el selector de fecha del panel Inicio y la barra superior."""
        caja = self.caja_actual()
        abierta = bool(caja) and caja["estado"] == "abierta"
        texto = f"{fecha_corta(fecha)} ({'r. abierta' if abierta else 'cerrada'})"
        if "inicio" in self.paneles:
            inicio = self.paneles["inicio"]
            if hasattr(inicio, 'actualizar_selector_caja'):
                inicio.actualizar_selector_caja(texto)
        self._actualizar_barra()

    def refrescar_todo(self):
        try:
            self._actualizar_selector_caja(self.caja_fecha)
        except tk.TclError:
            pass
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
        self.lbl_usuario_nombre.config(text=u["usuario"] if u else "")
        self.lbl_usuario_rango.config(text=(u["rango"] or "").upper() if u else "")
        self._actualizar_foto_nav((u["usuario"][:1].upper() if u else "?") or "?")
        caja = self.caja_actual()
        if not caja:
            return
        abierta = caja["estado"] == "abierta"
        r = db.resumen(caja["id"])
        self.lbl_pie_caja.config(text=f"Caja: {fecha_corta(caja['fecha'])}")
        self.lbl_pie_estado.config(
            text="ABIERTA" if abierta else "CERRADA",
            fg="#6EE7B7" if abierta else "#FCA5A5")
        self.lbl_pie_vendido.config(
            text=f"${r['total_vendido']:,.0f}".replace(",", "."))

    def _actualizar_foto_nav(self, inicial="?"):
        """Foto de perfil en círculo, o un círculo con la inicial del usuario."""
        c = self.canvas_avatar
        ruta = db.foto_perfil()
        if ruta:
            try:
                import os
                clave = ("foto", ruta, os.path.getmtime(ruta))
                if self._foto_nav_cache == clave and self._foto_nav_ref:
                    return
                foto = ic.foto_circular(ruta, 44)
                self._foto_nav_ref = foto
                self._foto_nav_cache = clave
                c.delete("all")
                c.create_image(22, 22, image=foto)
                return
            except Exception:
                pass
        clave = ("avatar", inicial)
        if self._foto_nav_cache == clave:
            return
        img = ic.avatar(inicial, 44, "#2B4A7A", "#FFFFFF")
        self._foto_nav_ref = img
        self._foto_nav_cache = clave
        c.delete("all")
        c.create_image(22, 22, image=img)

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
