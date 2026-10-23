# -*- coding: utf-8 -*-
"""Panel principal: CAJA DEL DÍA (diseño fiel a la especificación GARRAFAS)."""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import estilos as st
from util import money, fecha_larga, fecha_corta
from ui_cierre import CierreDialog


class InicioPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # Contenido con scroll vertical (área central scrollable,
        # barra superior y sidebar quedan fijas por main.py).
        self.contenido_scroll = st.contenido_scrollable(self)
        contenido = self.contenido_scroll

        # ================= CABECERA DE LA PÁGINA =================
        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(16, 8))
        self.cab = cab

        # Izquierda: círculo azul con garrafa blanca + título + fecha
        izq = tk.Frame(cab, bg=st.FONDO)
        izq.pack(side="left")

        # Círculo azul con ícono de garrafa (Canvas)
        self.canvas_icono_cab = tk.Canvas(
            izq, width=44, height=44, bg=st.FONDO,
            highlightthickness=0, bd=0)
        self.canvas_icono_cab.pack(side="left", padx=(0, 12))
        self._dibujar_icono_cabecera(self.canvas_icono_cab)

        col_titulo = tk.Frame(izq, bg=st.FONDO)
        col_titulo.pack(side="left")
        tk.Label(col_titulo, text="CAJA DEL DÍA", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        self.lbl_fecha_larga = tk.Label(col_titulo, text="", bg=st.FONDO,
                                        fg=st.TEXTO_SUAVE, font=(st.FUENTE, 12))
        self.lbl_fecha_larga.pack(anchor="w")

        # Estado de la caja: punto verde + "CAJA ABIERTA"
        self.lbl_estado_caja = tk.Label(col_titulo, text="● CAJA ABIERTA",
                                        bg=st.FONDO, fg=st.VERDE,
                                        font=(st.FUENTE, 11, "bold"))
        self.lbl_estado_caja.pack(anchor="w", pady=(2, 0))
        self.lbl_abierto_por = tk.Label(col_titulo, text="", bg=st.FONDO,
                                        fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10))
        self.lbl_abierto_por.pack(anchor="w")

        # Derecha: "Ver caja de la fecha:" + selector blanco con flecha
        der = tk.Frame(cab, bg=st.FONDO)
        der.pack(side="right")
        tk.Label(der, text="Ver caja de la fecha:", bg=st.FONDO,
                 fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10)).pack(anchor="e")
        # Selector blanco con borde sutil y esquinas redondeadas (Canvas)
        self.selector_caja = tk.Canvas(
            der, width=210, height=32, bg=st.FONDO,
            highlightthickness=0, bd=0, cursor="hand2")
        self.selector_caja.pack(anchor="e", pady=(2, 0))
        self.selector_caja.bind("<Button-1>", lambda e: self._abrir_selector_caja())
        self.lbl_selector_texto = self.selector_caja.create_text(
            105, 16, text="22/10/2026 (r. abierta)", fill=st.TEXTO,
            font=(st.FUENTE, 10, "bold"), anchor="center")
        self.selector_flecha = self.selector_caja.create_text(
            198, 16, text="▾", fill=st.TEXTO_SUAVE,
            font=(st.FUENTE, 10), anchor="center")
        self.selector_caja.create_rectangle(
            2, 2, 208, 30, outline=st.BORDE, width=1,
            tags=("borde",))
        st._redondeado(
            self.selector_caja, 2, 2, 208, 30, 16,
            fill=st.BLANCO, outline="", tags=("fondo_sel",))

        # ================= AVISO CAJAS SIN CERRAR =================
        self.banner = tk.Frame(contenido, bg=st.AMBAR_CLARO,
                               highlightbackground=st.AMBAR, highlightthickness=1)
        self.lbl_banner = tk.Label(self.banner, text="", bg=st.AMBAR_CLARO,
                                   fg=st.TEXTO, font=(st.FUENTE, 10),
                                   anchor="w", padx=12, pady=8)
        self.lbl_banner.pack(side="left", fill="x", expand=True)
        self.btn_banner = tk.Button(self.banner, text="Abrir y cerrar",
                                    command=self._abrir_pendiente,
                                    relief="flat", bg=st.AMBAR,
                                    fg="#ffffff", font=(st.FUENTE, 9, "bold"),
                                    padx=12, pady=6, cursor="hand2")

        # ================= TARJETAS DE MÉTRICAS =================
        tarjetas_fila1 = tk.Frame(contenido, bg=st.FONDO)
        tarjetas_fila1.pack(fill="x", padx=24, pady=(16, 8))
        tarjetas_fila2 = tk.Frame(contenido, bg=st.FONDO)
        tarjetas_fila2.pack(fill="x", padx=24, pady=(0, 8))

        # Fila 1: 4 tarjetas del mismo ancho
        definiciones_fila1 = [
            ("GARRAFAS VENDIDAS", "garrafas", st.COLOR_GARRAFA,
             lambda r: str(r["total_garrafas"]), None),
            ("TOTAL VENDIDO", "total", st.COLOR_TOTAL,
             lambda r: money(r["total_vendido"]), None),
            ("EFECTIVO", "efectivo", st.COLOR_EFECTIVO,
             lambda r: money(r["efectivo"]), None),
            ("TRANSFERENCIAS", "transferencia", st.COLOR_TRANS,
             lambda r: money(r["transferencias"]), None),
        ]

        self.cards = {}
        self.cards_detalle = {}
        for i, (titulo, clave, color, valor_fn, detalle_fn) in enumerate(definiciones_fila1):
            celda = tk.Frame(tarjetas_fila1, bg=st.FONDO)
            celda.pack(side="left", fill="both", expand=True, padx=6, pady=4)
            tarj = st.TarjetaMetrica(
                celda, titulo, "—", color_icono=color, detalle="",
                ancho=230, alto=110, fuente_valor=18)
            tarj.pack(fill="both", expand=True)
            self.cards[clave] = tarj
            self.cards_detalle[clave] = detalle_fn

        # Fila 2: 3 tarjetas (primera y segunda más anchas, tercera normal)
        definiciones_fila2 = [
            ("TARJETAS", "tarjetas", st.COLOR_TARJETA,
             lambda r: money(r["debito"] + r["credito"]),
             lambda r: f"Débito {money(r['debito'])}  •  Crédito {money(r['credito'])}"),
            ("TOTAL GENERAL", "general", st.TURQUESA,
             lambda r: money(r["total_general"]), None),
            ("VENTAS REGISTRADAS", "cantidad", st.VIOLETA,
             lambda r: str(r["cantidad_ventas"]), None),
        ]

        for i, (titulo, clave, color, valor_fn, detalle_fn) in enumerate(definiciones_fila2):
            celda = tk.Frame(tarjetas_fila2, bg=st.FONDO)
            if i < 2:
                celda.pack(side="left", fill="both", expand=True, padx=6, pady=4)
            else:
                celda.pack(side="left", fill="both", expand=False, padx=6, pady=4)
            tarj = st.TarjetaMetrica(
                celda, titulo, "—", color_icono=color, detalle="",
                ancho=270 if i < 2 else 210, alto=110, fuente_valor=18)
            tarj.pack(fill="both", expand=True)
            self.cards[clave] = tarj
            self.cards_detalle[clave] = detalle_fn

        # ================= BOTONES DE ACCIÓN =================
        marco_accion = tk.Frame(contenido, bg=st.FONDO)
        marco_accion.pack(fill="x", padx=24, pady=(16, 0))

        self.btn_abrir = st.BotonAccion(
            marco_accion, texto="CAJA ABIERTA — Usuario",
            color=st.VERDE, comando=self._abrir_caja,
            ancho=320, alto=76, radio=10, icono_texto="🔓")
        self.btn_abrir.pack(side="left", fill="x", expand=True,
                            padx=(0, 12))

        self.btn_cierre = st.BotonAccion(
            marco_accion, texto="CERRAR CAJA — Usuario",
            color=st.ACENTO, comando=self._abrir_cierre,
            ancho=320, alto=76, radio=10, icono_texto="🔒")
        self.btn_cierre.pack(side="left", fill="x", expand=True,
                             padx=(12, 0))

        # ================= TEXTO INFORMATIVO =================
        self.lbl_pie = tk.Label(
            contenido,
            text="i  Al finalizar la jornada presioná el botón, revisá el resumen del día, "
                 "contá los billetes y confirmá el cierre.",
            bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10),
            wraplength=880, anchor="w", justify="left")
        self.lbl_pie.pack(fill="x", padx=24, pady=(12, 20))

        # ================= VENTAS POR PRODUCTO =================
        # Tarjeta blanca con esquinas redondeadas (Canvas)
        self.tarjeta_productos = tk.Canvas(
            contenido, bg=st.FONDO, highlightthickness=0, bd=0)
        self.tarjeta_productos.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Fondo blanco de la tarjeta
        self.fondo_tarjeta_prod = st._redondeado(
            self.tarjeta_productos, 0, 0, 1, 1, 12,
            fill=st.TARJETA, outline=st.BORDE, width=1, tags=("fondo",))
        # Encabezado de la tarjeta
        self.lbl_enc_prod = tk.Label(
            self.tarjeta_productos, text="VENTAS POR PRODUCTO",
            bg=st.TARJETA, fg=st.TEXTO, font=(st.FUENTE, 12, "bold"),
            anchor="w")
        self.win_enc_prod = self.tarjeta_productos.create_window(
            16, 14, window=self.lbl_enc_prod, anchor="nw", tags=("enc",))

        # Contenedor interno scrollable para filas de producto
        self.contenedor_producto = tk.Frame(
            self.tarjeta_productos, bg=st.TARJETA)
        self.win_contenido_prod = self.tarjeta_productos.create_window(
            0, 60, window=self.contenedor_producto,
            anchor="nw", tags=("contenido",))

        # Vincular eventos de redimensionamiento
        self.tarjeta_productos.bind("<Configure>", self._ajustar_tarjeta_prod)
        self.contenedor_producto.bind("<Configure>", self._ajustar_scroll_prod)

        self.filas_producto = {}
        self.mensaje_vacio = None

    # ------------------------------------------------------------------ Iconos Canvas
    def _dibujar_icono_cabecera(self, canvas):
        """Dibuja una garrafa blanca dentro de un círculo azul."""
        w = h = 44
        cx = cy = w // 2
        r = 18
        st._circulo(canvas, cx, cy, r, fill=st.ACENTO, outline="", tags=("ico",))
        # Garrafa blanca simplificada
        st._linea(canvas, cx - 10, cy + 6, cx + 10, cy + 6, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx - 8, cy + 6, cx - 13, cy - 2, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx + 8, cy + 6, cx + 13, cy - 2, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx - 13, cy - 2, cx + 13, cy - 2, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx - 7, cy - 2, cx - 7, cy - 10, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx + 7, cy - 2, cx + 7, cy - 10, st.BLANCO, 2, ("ico",))
        st._linea(canvas, cx - 7, cy - 10, cx + 7, cy - 10, st.BLANCO, 2, ("ico",))

    # ------------------------------------------------------------------ Acciones
    def _sin_permiso_ventas(self):
        if db.puede("ventas"):
            return False
        messagebox.showerror("Sin permisos",
                             "Tu usuario no tiene permiso para operar ventas.",
                             parent=self)
        return True

    def _abrir_caja(self):
        if not db.puede("abrir_caja"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no tiene permiso para abrir cajas.",
                                 parent=self)
            return
        caja = self.app.caja_actual()
        from ui_inicio import AbrirCajaDialog
        AbrirCajaDialog(self.app, caja,
                        on_abierto=lambda: self.app.refrescar_todo())

    def _abrir_cierre(self):
        if not db.puede("cerrar_caja"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no tiene permiso para cerrar cajas.",
                                 parent=self)
            return
        caja = self.app.caja_actual()
        if not caja:
            return
        if caja["estado"] != "abierta":
            messagebox.showinfo(
                "Caja cerrada",
                "Esta caja ya fue cerrada y está bloqueada.\n"
                "Si necesitás modificar algo, usá la reapertura de caja "
                "desde Historial de cierres.",
                parent=self)
            return

        r = db.resumen(caja["id"])

        # -------- Caja sin ventas: cierre directo, sin arqueo ni contraseña ----
        if r["cantidad_ventas"] == 0:
            if not messagebox.askyesno(
                "Cerrar caja",
                f"Caja del {db.fecha_larga(caja['fecha'])} "
                "sin ventas cargadas.\n\n"
                "Se cerrará definitivamente, sin arqueo de billetes.\n\n"
                "¿Cerrar la caja ahora?",
                parent=self):
                return
            fondo = float(r.get("fondo") or 0)
            try:
                db.guardar_cierre(
                    caja["id"],
                    total_garrafas=0, total_vendido=0,
                    efectivo_esperado=fondo, efectivo_contado=fondo,
                    transferencias=0, debito=0, credito=0, bono=0,
                    total_general=0, diferencia=0, estado="Cuadrada",
                    billetes={}, n_transferencias=0,
                )
            except Exception as e:
                messagebox.showerror("No se pudo cerrar", str(e), parent=self)
                return
            try:
                db.respaldar("cierre de caja")
            except Exception:
                pass
            self.app.refrescar_todo()
            return

        # -------- Con ventas: arqueo completo (diálogo + contraseña) --------
        def al_cerrar():
            self.app.refrescar_todo()
            self.app.mostrar("inicio")

        CierreDialog(self.app, caja, on_cerrado=al_cerrar)

    def _abrir_selector_caja(self):
        """Muestra el menú de selección de caja usando el método de la app principal."""
        self.app._abrir_selector_caja()

    def actualizar_selector_caja(self, texto):
        """Actualiza el texto del selector de caja en la cabecera."""
        self.selector_caja.itemconfig(self.lbl_selector_texto, text=texto)

    def _abrir_pendiente(self):
        pendientes = [c for c in db.cajas_abiertas()
                      if c["fecha"] != self.app.caja_fecha]
        if pendientes:
            self.app.cambiar_caja(pendientes[0]["fecha"])

    def _seleccionar_caja(self, _=None):
        # El selector es visual; la selección real se hace por el banner o menú.
        pass

    def _usuario_txt(self):
        u = db.usuario_sesion()
        return u["usuario"] if u else "—"

    # ------------------------------------------------------------------ Refresco
    def _ajustar_tarjeta_prod(self, evento=None):
        w = self.tarjeta_productos.winfo_width()
        h = self.tarjeta_productos.winfo_height()
        self.tarjeta_productos.coords(
            self.fondo_tarjeta_prod, 0, 0, w, h)
        self.tarjeta_productos.itemconfig(
            self.fondo_tarjeta_prod,
            width=0)
        self.tarjeta_productos.delete(self.fondo_tarjeta_prod)
        self.fondo_tarjeta_prod = st._redondeado(
            self.tarjeta_productos, 0, 0, w, h, 12,
            fill=st.TARJETA, outline=st.BORDE, width=1, tags=("fondo",))
        self.tarjeta_productos.tag_lower(self.fondo_tarjeta_prod)
        self.tarjeta_productos.coords(self.win_enc_prod, 16, 14)
        self.tarjeta_productos.coords(self.win_contenido_prod, 0, 60)
        self.tarjeta_productos.itemconfig(
            self.win_contenido_prod, width=w - 32)

    def _ajustar_scroll_prod(self, evento=None):
        self.tarjeta_productos.configure(
            scrollregion=self.tarjeta_productos.bbox("all"))

    def refresh(self):
        caja = self.app.caja_actual()
        if not caja:
            return

        fecha = caja["fecha"]
        self.lbl_fecha_larga.config(text=fecha_larga(fecha))

        # Estado de caja
        if caja["estado"] == "abierta":
            self.lbl_estado_caja.config(text="● CAJA ABIERTA", fg=st.VERDE)
            apertura = db.apertura_de(caja["id"])
            if apertura:
                self.btn_abrir.configurar_estado(
                    False,
                    texto=f"CAJA ABIERTA — {apertura['usuario']} "
                          f"{(apertura['hora'] or '')[:5]}",
                    color="#94a3b8")
                self.lbl_abierto_por.config(
                    text=f"Abierta por {apertura['usuario']} a las "
                         f"{(apertura['hora'] or '')[:5]} — monto inicial "
                         f"{money(apertura['monto_inicial'] or 0)}")
            else:
                self.btn_abrir.configurar_estado(
                    True,
                    texto=f"ABRIR CAJA — {self._usuario_txt()}",
                    color=st.VERDE)
                self.lbl_abierto_por.config(text="")

            if db.puede("cerrar_caja"):
                self.btn_cierre.configurar_estado(
                    True,
                    texto=f"CERRAR CAJA — {self._usuario_txt()}",
                    color=st.ACENTO)
            else:
                self.btn_cierre.configurar_estado(
                    False,
                    texto="SIN PERMISOS PARA CERRAR",
                    color="#94a3b8")

            self.lbl_pie.config(
                text="i  Al finalizar la jornada presioná el botón, revisá el "
                     "resumen del día, contá los billetes y confirmá el cierre.")
        else:
            self.lbl_estado_caja.config(text="■ CAJA CERRADA", fg=st.ROJO)
            self.btn_abrir.configurar_estado(
                False, texto="CAJA CERRADA", color="#94a3b8")
            self.btn_cierre.configurar_estado(
                False, texto="CAJA CERRADA — BLOQUEADA", color="#94a3b8")
            self.lbl_abierto_por.config(text="")
            cierre = db.get_cierre_activo(caja["id"])
            if cierre:
                estado = cierre["estado"]
                self.lbl_pie.config(
                    text=(
                        f"Cierre del {fecha_corta(cierre['fecha'])} a las "
                        f"{cierre['hora_cierre']} — Total vendido "
                        f"{money(cierre['total_vendido'])} — Diferencia "
                        f"{money(cierre['diferencia'])} — Estado: {estado}. "
                        f"La caja está bloqueada."
                    ),
                    fg=st.TEXTO_SUAVE)

        # Resumen en cards
        r = db.resumen(caja["id"])
        self.cards["garrafas"].actualizar_valor(str(r["total_garrafas"]))
        self.cards["total"].actualizar_valor(money(r["total_vendido"]))
        self.cards["efectivo"].actualizar_valor(money(r["efectivo"]))
        self.cards["transferencia"].actualizar_valor(money(r["transferencias"]))
        self.cards["tarjetas"].actualizar_valor(
            money(r["debito"] + r["credito"]),
            detalle=f"Débito {money(r['debito'])}  •  Crédito {money(r['credito'])}")
        self.cards["general"].actualizar_valor(money(r["total_general"]))
        self.cards["cantidad"].actualizar_valor(str(r["cantidad_ventas"]))

        # Ventas por producto
        for w in self.contenedor_producto.winfo_children():
            w.destroy()
        vendidos = [(pid, info) for pid, info in r["por_producto"].items()
                    if int(info["cantidad"]) > 0]
        if not vendidos:
            vacio = tk.Frame(self.contenedor_producto, bg="#EEF2F8",
                             highlightbackground=st.BORDE, highlightthickness=1)
            vacio.pack(fill="x", pady=30, padx=40)
            # Icono "i" en círculo
            cv = tk.Canvas(vacio, width=32, height=32, bg="#EEF2F8",
                           highlightthickness=0, bd=0)
            cv.pack(pady=(16, 4))
            st._circulo(cv, 16, 16, 14, fill="#BFDBFE", outline="", tags=("ico",))
            st._linea(cv, 16, 10, 16, 22, st.ACENTO, 2, ("ico",))
            st._linea(cv, 16, 26, 16, 28, st.ACENTO, 2, ("ico",))
            tk.Label(vacio, text="Todavía no se vendió nada en esta caja.",
                     bg="#EEF2F8", fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 11)).pack(pady=(0, 16))
        else:
            for pid, info in vendidos:
                fila = tk.Frame(self.contenedor_producto, bg=st.TARJETA)
                fila.pack(fill="x", pady=1)
                tk.Label(fila, text=f"• {info['nombre']}", bg=st.TARJETA,
                         fg=st.TEXTO, font=(st.FUENTE, 11),
                         anchor="w").pack(side="left", padx=12)
                tk.Label(fila, text=f"{info['cantidad']} unidades",
                         bg=st.TARJETA, fg=st.TEXTO_SUAVE,
                         font=(st.FUENTE, 10),
                         anchor="e").pack(side="right", padx=(0, 12))
                tk.Label(fila, text=money(info["total"]), bg=st.TARJETA,
                         fg=st.TEXTO, font=(st.FUENTE, 11, "bold"),
                         width=14, anchor="e").pack(side="right", padx=12)

            separador = tk.Frame(self.contenedor_producto, bg=st.BORDE, height=1)
            separador.pack(fill="x", pady=(6, 2), padx=12)
            total = tk.Frame(self.contenedor_producto, bg=st.TARJETA)
            total.pack(fill="x")
            unidades_t = sum(int(info["cantidad"]) for _pid, info in vendidos)
            dinero_t = sum(float(info["total"]) for _pid, info in vendidos)
            tk.Label(total, text="TOTAL GENERAL", bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 12, "bold"), anchor="w").pack(
                         side="left", padx=12, pady=8)
            tk.Label(total, text=f"{unidades_t} unidades", bg=st.TARJETA,
                     fg=st.VERDE_OSCURO, font=(st.FUENTE, 11, "bold"),
                     anchor="e").pack(side="right", padx=(0, 12))
            tk.Label(total, text=money(dinero_t), bg=st.TARJETA,
                     fg=st.VERDE_OSCURO, font=(st.FUENTE, 12, "bold"),
                     width=14, anchor="e").pack(side="right", padx=12)


class AbrirCajaDialog(tk.Toplevel):
    """Diálogo para abrir la caja del día registrando el monto inicial."""

    def __init__(self, master, caja, on_abierto=None):
        super().__init__(master)
        self.caja = caja
        self.on_abierto = on_abierto
        self.title("Abrir caja")
        self.configure(bg=st.BARRA)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        ancho, alto = 460, 380
        self.geometry(f"{ancho}x{alto}")
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2 - 40)
        self.geometry(f"+{x}+{y}")

        cont = tk.Frame(self, bg=st.BARRA)
        cont.pack(fill="both", expand=True, padx=36, pady=(30, 26))

        tk.Label(cont, text="APERTURA DE CAJA", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 20, "bold")).pack(anchor="w")
        u = db.usuario_sesion()
        tk.Label(cont,
                 text=f"Fecha: {db.fecha_larga(self.caja['fecha'])}   —   "
                      f"Usuario: {u['usuario'] if u else '—'}",
                 bg=st.BARRA, fg="#9fb0cc", font=(st.FUENTE, 9)).pack(
            anchor="w", pady=(2, 20))

        tk.Label(cont, text="MONTO INICIAL (fondo de caja)", bg=st.BARRA,
                 fg="#c7d2e4", font=(st.FUENTE, 9, "bold")).pack(anchor="w")
        self.var = tk.StringVar(value=money(db.get_fondo_inicial()))
        ent = tk.Entry(cont, textvariable=self.var, font=(st.FUENTE, 14),
                       relief="solid", bd=1, justify="left")
        ent.pack(fill="x", pady=(4, 20), ipady=5)

        btnCancelar = tk.Button(
            cont, text="CANCELAR", command=self._cancelar,
            relief="flat", bg="#3b4a6b", fg="#ffffff",
            font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
            cursor="hand2")
        btnCancelar.pack(side="left", fill="x", expand=True)

        btnAbrir = tk.Button(
            cont, text="ABRIR CAJA", command=self._abrir,
            relief="flat", bg=st.VERDE, fg="#ffffff",
            font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
            cursor="hand2")
        btnAbrir.pack(side="left", fill="x", expand=True, padx=(10, 0))
        btnAbrir.bind("<Enter>",
                      lambda e: btnAbrir.config(bg=st.VERDE_OSCURO))
        btnAbrir.bind("<Leave>",
                      lambda e: btnAbrir.config(bg=st.VERDE))

        ent.focus_set()

    def _cancelar(self):
        self.destroy()

    def _abrir(self):
        try:
            monto = float(self.var.get().replace("$", "").replace(".", "").strip() or 0)
        except ValueError:
            messagebox.showerror("Monto inválido",
                                 "Ingresá un monto inicial válido.",
                                 parent=self)
            return
        db.registrar_apertura(self.caja["id"], monto)
        if self.on_abierto:
            self.on_abierto()
        self.destroy()
