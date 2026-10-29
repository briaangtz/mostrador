# -*- coding: utf-8 -*-
"""Panel principal: CAJA DEL DÍA (diseño Figma "GARRAFAS — Caja del día")."""

import re
import tkinter as tk
from tkinter import messagebox, simpledialog

import database as db
import errores
import estilos as st
import iconos as ic
from util import money, parse_numero, fecha_larga, fecha_corta
from ui_cierre import CierreDialog
from widgets_figma import Tarjeta, Boton

PADX = 28                       # margen lateral de la página
MUTED = st.TEXTO_SUAVE
AZUL = "#2563EB"
AZUL_CLARO = "#E8F0FE"
GRIS_ICONO = "#64748B"
GRIS_CLARO = "#F1F5F9"
# Estados de la caja (fondo de la franja, borde)
ABIERTA_BG, ABIERTA_BORDE = "#ECF7F0", "#BDE5CD"
CERRADA_BG, CERRADA_BORDE = "#FDEEEE", "#F5C2C2"


def _lbl(parent, texto="", size=10, color=None, bold=False, **kw):
    return tk.Label(parent, text=texto, bg=parent.cget("bg"),
                    fg=color or st.TEXTO,
                    font=(st.FUENTE, size, "bold") if bold else (st.FUENTE, size),
                    **kw)


def _num_caja(caja):
    """Número de caja para el pie (001, 002…). Si no se puede, queda vacío."""
    try:
        claves = list(caja.keys())
        for k in ("numero", "nro", "caja_numero", "num"):
            if k in claves:
                return f"{int(caja[k]):03d}"
        return f"{int(caja['id']):03d}"
    except Exception:
        return ""


class InicioPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._construir()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # Área central con scroll (barra superior y sidebar las maneja main.py)
        self.contenido_scroll = st.contenido_scrollable(self)
        c = self.contenido_scroll

        # ================= CABECERA DE LA PÁGINA =================
        cab = tk.Frame(c, bg=st.FONDO)
        cab.pack(fill="x", padx=PADX, pady=(22, 10))
        self.cab = cab

        izq = tk.Frame(cab, bg=st.FONDO)
        izq.pack(side="left")
        _lbl(izq, "Caja del día", 24, st.TEXTO, True).pack(anchor="w")
        self.lbl_fecha_larga = _lbl(izq, "", 11, MUTED)
        self.lbl_fecha_larga.pack(anchor="w", pady=(2, 0))

        der = tk.Frame(cab, bg=st.FONDO)
        der.pack(side="right")
        _lbl(der, "Ver caja de la fecha", 9, MUTED).pack(anchor="e")

        # Selector de fecha: tarjeta blanca redondeada con calendario y flecha
        self.selector_caja = Tarjeta(der, radio=10, padx=12, pady=8,
                                     borde="#D9E0EC", ancho=236)
        self.selector_caja.pack(anchor="e", pady=(3, 0))
        sc = self.selector_caja.cuerpo
        self._ico_sel_flecha = tk.Label(sc, image=ic.icono("chevron", 16, GRIS_ICONO),
                                        bg=st.TARJETA)
        self._ico_sel_flecha.pack(side="right")
        tk.Label(sc, image=ic.icono("calendar", 18, GRIS_ICONO),
                 bg=st.TARJETA).pack(side="left", padx=(0, 8))
        self.lbl_selector_fecha = _lbl(sc, "", 11, st.TEXTO)
        self.lbl_selector_fecha.configure(bg=st.TARJETA)
        self.lbl_selector_fecha.pack(side="left")
        self.lbl_selector_estado = _lbl(sc, "", 9, MUTED)
        self.lbl_selector_estado.configure(bg=st.TARJETA)
        self.lbl_selector_estado.pack(side="left", padx=(8, 8))
        for w in (self.selector_caja, sc, *sc.winfo_children()):
            w.bind("<Button-1>", lambda e: self._abrir_selector_caja())
            w.configure(cursor="hand2")

        # ================= AVISO CAJAS SIN CERRAR =================
        # (se mantiene igual: lo maneja la lógica existente)
        self.banner = tk.Frame(c, bg=st.AMBAR_CLARO,
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

        # ================= FRANJA DE ESTADO DE LA CAJA =================
        self.estado_card = Tarjeta(c, fondo=ABIERTA_BG, borde=ABIERTA_BORDE,
                                   radio=12, padx=18, pady=14)
        self.estado_card.pack(fill="x", padx=PADX, pady=(4, 0))
        ec = self.estado_card.cuerpo
        ec.columnconfigure(1, weight=1)
        self.ico_estado = tk.Label(ec, bg=ABIERTA_BG)
        self.ico_estado.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        self.lbl_estado_titulo = _lbl(ec, "Caja abierta", 14, st.VERDE_OSCURO)
        self.lbl_estado_titulo.configure(bg=ABIERTA_BG)
        self.lbl_estado_titulo.grid(row=0, column=1, sticky="sw")
        self.lbl_estado_sub = _lbl(ec, "", 10, MUTED)
        self.lbl_estado_sub.configure(bg=ABIERTA_BG)
        self.lbl_estado_sub.grid(row=1, column=1, sticky="nw")
        # Compatibilidad con el código anterior
        self.lbl_estado_caja = self.lbl_estado_titulo
        self.lbl_abierto_por = self.lbl_estado_sub

        self.f_monto = tk.Frame(ec, bg=ABIERTA_BG)
        self.f_monto.grid(row=0, column=2, rowspan=2, sticky="e")
        self.lbl_monto_t = _lbl(self.f_monto, "Monto inicial", 9, MUTED)
        self.lbl_monto_t.configure(bg=ABIERTA_BG)
        self.lbl_monto_t.pack(anchor="e")
        self.lbl_monto = _lbl(self.f_monto, "$0", 18, st.TEXTO)
        self.lbl_monto.configure(bg=ABIERTA_BG)
        self.lbl_monto.pack(anchor="e")
        self.btn_abrir = Boton(ec, "Abrir caja", st.VERDE, self._abrir_caja,
                               icono="unlock", alto=42, ancho=210,
                               exterior=ABIERTA_BG, tam=11)
        self.btn_abrir.grid(row=0, column=2, rowspan=2, sticky="e")
        self.btn_abrir.grid_remove()
        # Botón de reapertura: aparece cuando la caja del día está CERRADA,
        # para poder reabrirla directamente desde acá (antes solo desde Historial).
        self.btn_reabrir = Boton(ec, "Reabrir caja", st.ROJO, self._reabrir_caja,
                                 icono="unlock", alto=42, ancho=210,
                                 exterior=CERRADA_BG, tam=11)
        self.btn_reabrir.grid(row=0, column=2, rowspan=2, sticky="e")
        self.btn_reabrir.grid_remove()
        self._estado_widgets = [ec, self.ico_estado, self.lbl_estado_titulo,
                                self.lbl_estado_sub, self.f_monto,
                                self.lbl_monto_t, self.lbl_monto]
        self._pintar_estado(True)

        # ================= RESUMEN DE LA JORNADA =================
        t1 = tk.Frame(c, bg=st.FONDO)
        t1.pack(fill="x", padx=PADX, pady=(20, 8))
        _lbl(t1, "Resumen de la jornada", 13, st.TEXTO).pack(side="left")
        _lbl(t1, "Importes de la caja actual", 9, MUTED).pack(side="right")

        fila_m = tk.Frame(c, bg=st.FONDO)
        fila_m.pack(fill="x", padx=PADX)
        for i in range(3):
            fila_m.columnconfigure(i, weight=1, uniform="m")
        self.v_total = self._metrica(fila_m, 0, "Total vendido", "dollar",
                                     AZUL, AZUL_CLARO, "#C3D6F8")
        self.v_garrafas = self._metrica(fila_m, 1, "Garrafas vendidas", "cube",
                                        GRIS_ICONO, GRIS_CLARO)
        self.v_cantidad = self._metrica(fila_m, 2, "Ventas registradas",
                                        "clipboard", GRIS_ICONO, GRIS_CLARO)

        # ================= DESGLOSE POR MEDIO DE PAGO =================
        des = Tarjeta(c, radio=12, padx=20, pady=16)
        des.pack(fill="x", padx=PADX, pady=(14, 0))
        dc = des.cuerpo
        h = tk.Frame(dc, bg=st.TARJETA)
        h.pack(fill="x")
        _lbl(h, "Desglose por medio de pago", 11, st.TEXTO).pack(side="left")
        _lbl(h, "Pesos ($)", 9, MUTED).pack(side="right")

        g = tk.Frame(dc, bg=st.TARJETA)
        g.pack(fill="x", pady=(12, 0))
        for i in range(4):
            g.columnconfigure(i, weight=1, uniform="d")
        self.v_efectivo, self.d_efectivo = self._medio(
            g, 0, "Efectivo", "banknote")
        self.v_transf, self.d_transf = self._medio(
            g, 1, "Transferencias", "transfer")
        self.v_tarjetas, self.d_tarjetas = self._medio(
            g, 2, "Tarjetas", "card")
        # Total general (separado por una línea vertical)
        col = tk.Frame(g, bg=st.TARJETA)
        col.grid(row=0, column=3, sticky="nsew")
        tk.Frame(col, bg=st.BORDE, width=1).pack(side="left", fill="y")
        tot = tk.Frame(col, bg=st.TARJETA)
        tot.pack(side="left", fill="both", expand=True, padx=(22, 0))
        _lbl(tot, "Total general", 10, st.TEXTO, True).pack(anchor="w")
        self.v_general = _lbl(tot, "$0", 22, st.TEXTO)
        self.v_general.pack(anchor="w", pady=(4, 2))
        self.d_general = _lbl(tot, "Todos los medios de pago", 9, MUTED)
        self.d_general.pack(anchor="w")

        # ================= VENTAS POR PRODUCTO + CIERRE =================
        fila_b = tk.Frame(c, bg=st.FONDO)
        fila_b.pack(fill="both", expand=True, padx=PADX, pady=(14, 0))
        fila_b.columnconfigure(0, weight=7)
        fila_b.columnconfigure(1, weight=3, minsize=290)
        fila_b.rowconfigure(0, weight=1)

        # ---- Ventas por producto ----
        vp = Tarjeta(fila_b, radio=12, padx=0, pady=0)
        vp.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        vc = vp.cuerpo
        hv = tk.Frame(vc, bg=st.TARJETA)
        hv.pack(fill="x", padx=20, pady=(14, 12))
        tk.Label(hv, image=ic.icono("bars", 20, GRIS_ICONO), bg=st.TARJETA
                 ).pack(side="left", padx=(0, 10))
        _lbl(hv, "Ventas por producto", 12, st.TEXTO).pack(side="left")
        tk.Frame(vc, bg=st.BORDE, height=1).pack(fill="x")
        self.contenedor_producto = tk.Frame(vc, bg=st.TARJETA)
        self.contenedor_producto.pack(fill="both", expand=True, padx=20, pady=16)

        # ---- Cierre de jornada ----
        cj = Tarjeta(fila_b, radio=12, padx=20, pady=16)
        cj.grid(row=0, column=1, sticky="nsew")
        cc = cj.cuerpo
        hc = tk.Frame(cc, bg=st.TARJETA)
        hc.pack(fill="x")
        tk.Label(hc, image=ic.icono("lock", 20, GRIS_ICONO), bg=st.TARJETA
                 ).pack(side="left", padx=(0, 10))
        _lbl(hc, "Cierre de jornada", 12, st.TEXTO).pack(side="left")
        self.lbl_pie = _lbl(
            cc, "Al finalizar la jornada, revisá el resumen del día, contá "
                "los billetes y confirmá el cierre.", 10, MUTED,
            anchor="w", justify="left", wraplength=240)
        self.lbl_pie.pack(fill="x", pady=(14, 12))
        cc.bind("<Configure>", lambda e: self.lbl_pie.configure(
            wraplength=max(120, e.width - 4)))
        resp = tk.Frame(cc, bg=st.TARJETA)
        resp.pack(fill="x")
        _lbl(resp, "Responsable de caja", 9, MUTED).pack(side="left")
        self.lbl_responsable = _lbl(resp, "—", 10, st.TEXTO, True)
        self.lbl_responsable.pack(side="right")
        self.btn_cierre = Boton(cc, "Cerrar caja", AZUL, self._abrir_cierre,
                                icono="lock", alto=48, exterior=st.TARJETA)
        self.btn_cierre.pack(fill="x", pady=(14, 0))

        # ================= PIE =================
        pie = tk.Frame(c, bg=st.FONDO)
        pie.pack(fill="x", padx=PADX, pady=(16, 24))
        _lbl(pie, "DOBLE G SRL / MOSTRADOR", 9, MUTED).pack(side="left")
        self.lbl_pie_caja = _lbl(pie, "", 9, MUTED)
        self.lbl_pie_caja.pack(side="right")

    # ------------------------------------------------------------------ piezas
    def _metrica(self, fila, col, titulo, icono, color_ico, fondo_ico,
                 borde=None):
        t = Tarjeta(fila, radio=12, padx=20, pady=16, borde=borde)
        t.grid(row=0, column=col, sticky="nsew",
               padx=(0 if col == 0 else 7, 0 if col == 2 else 7))
        cu = t.cuerpo
        top = tk.Frame(cu, bg=st.TARJETA)
        top.pack(fill="x")
        _lbl(top, titulo, 11, MUTED).pack(side="left")
        tk.Label(top, image=ic.cuadro(icono, 34, color_ico, fondo_ico, 8, 18),
                 bg=st.TARJETA).pack(side="right")
        v = _lbl(cu, "0", 28, st.TEXTO)
        v.pack(anchor="w", pady=(10, 0))
        return v

    def _medio(self, g, col, titulo, icono):
        f = tk.Frame(g, bg=st.TARJETA)
        f.grid(row=0, column=col, sticky="nsew", padx=(0, 18))
        top = tk.Frame(f, bg=st.TARJETA)
        top.pack(anchor="w")
        tk.Label(top, image=ic.icono(icono, 18, GRIS_ICONO), bg=st.TARJETA
                 ).pack(side="left", padx=(0, 8))
        _lbl(top, titulo, 10, MUTED).pack(side="left")
        v = _lbl(f, "$0", 20, st.TEXTO, True)
        v.pack(anchor="w", pady=(6, 2))
        d = _lbl(f, "", 9, MUTED)
        d.pack(anchor="w")
        return v, d

    def _pintar_estado(self, abierta):
        """Colorea la franja de estado: verde (abierta) o rojo (cerrada)."""
        bg, borde = (ABIERTA_BG, ABIERTA_BORDE) if abierta else (CERRADA_BG, CERRADA_BORDE)
        self.estado_card.pintar(fondo=bg, borde=borde)
        for w in self._estado_widgets:
            w.configure(bg=bg)
        self.btn_abrir.pintar(exterior=bg)
        self.btn_reabrir.pintar(exterior=bg)
        color = st.VERDE_OSCURO if abierta else st.ROJO
        self.lbl_estado_titulo.configure(
            text="Caja abierta" if abierta else "Caja cerrada", fg=color)
        self.ico_estado.configure(image=ic.cuadro(
            "unlock" if abierta else "lock", 46, color, "#FFFFFF", 10, 22,
            borde="#D6EBDD" if abierta else "#F3CFCF"))

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
        try:
            caja = self.app.caja_actual()
            if not caja:
                messagebox.showerror("Sin caja",
                                     "No se encontró la caja del día.",
                                     parent=self)
                return
            AbrirCajaDialog(self.app, caja,
                            on_abierto=lambda: self.app.refrescar_todo())
        except Exception as e:
            errores.mostrar(
                "No se pudo abrir la caja", e, parent=self,
                contexto="abrir la caja del día",
                mensaje="No se pudo abrir la caja del día.\n"
                        "Probá de nuevo; si sigue fallando, reiniciá el "
                        "programa.")

    def _reabrir_caja(self):
        """Reabre la caja del día si está cerrada (solo DESARROLLADOR,
        con contraseña). Mismo flujo que Historial de cierres."""
        if not db.puede("reabrir_caja"):
            messagebox.showerror(
                "Sin permisos",
                "Solo un usuario con rango DESARROLLADOR puede reabrir cajas.",
                parent=self)
            return
        try:
            caja = self.app.caja_actual()
            if not caja:
                return
            if caja["estado"] == "abierta":
                messagebox.showinfo("Caja abierta",
                                    "Esta caja ya está abierta.",
                                    parent=self)
                return

            u = db.usuario_sesion() or {}
            password = simpledialog.askstring(
                "Reapertura de caja",
                f"Caja del {fecha_corta(caja['fecha'])}\n\n"
                f"Usuario: {u.get('usuario', '—')}\n"
                "Ingresá TU contraseña para autorizar la reapertura:",
                parent=self, show="*")
            if password is None:
                return
            if not db.validar_password_sesion(password):
                messagebox.showerror(
                    "Reapertura denegada",
                    "Contraseña incorrecta. La caja permanece cerrada.",
                    parent=self)
                return

            if not messagebox.askyesno(
                "Reabrir caja",
                f"Se anulará el cierre del {fecha_corta(caja['fecha'])} y la "
                "caja volverá a quedar abierta para modificaciones.\n\n"
                "¿Continuar?",
                parent=self):
                return

            db.reabrir_caja(caja["id"])
            messagebox.showinfo(
                "Caja reabierta",
                "La caja fue reabierta. Ya podés cargar ventas y volver a "
                "cerrarla.",
                parent=self)
            self.app.refrescar_todo()
        except Exception as e:
            errores.mostrar(
                "No se pudo reabrir la caja", e, parent=self,
                contexto="reabrir la caja",
                mensaje="No se pudo reabrir la caja.\n"
                        "La caja sigue cerrada; probá de nuevo.")

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
                errores.mostrar(
                    "No se pudo cerrar", e, parent=self,
                    contexto="guardar el cierre de caja",
                    mensaje="No se pudo guardar el cierre.\n"
                            "La caja NO se cerró: probá de nuevo.")
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
        """Actualiza el selector de fecha de la cabecera.

        Acepta textos como '22/10/2026 (• abierta)' y los muestra como
        '22/10/2026  (r. abierta)', igual que el diseño."""
        texto = (texto or "").replace("•", "r.")
        m = re.match(r"^\s*(\S+)\s*(\(.*\))?\s*$", texto)
        fecha, estado = (m.group(1), m.group(2) or "") if m else (texto, "")
        self.lbl_selector_fecha.config(text=fecha)
        self.lbl_selector_estado.config(text=estado)

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
    def refresh(self):
        caja = self.app.caja_actual()
        if not caja:
            return

        fecha = caja["fecha"]
        txt = fecha_larga(fecha)
        self.lbl_fecha_larga.config(text=txt[:1].upper() + txt[1:])
        self.lbl_pie_caja.config(text=fecha_corta(fecha))
        if not self.lbl_selector_fecha.cget("text"):
            self.actualizar_selector_caja(
                f"{fecha_corta(fecha)} "
                f"({'r. abierta' if caja['estado'] == 'abierta' else 'cerrada'})")

        usuario = self._usuario_txt()
        abierta = caja["estado"] == "abierta"
        self._pintar_estado(abierta)

        if abierta:
            self.btn_reabrir.grid_remove()
            apertura = db.apertura_de(caja["id"])
            if apertura:
                hora = (apertura["hora"] or "")[:5]
                self.lbl_estado_sub.config(
                    text=f"Abierta por {apertura['usuario']} a las {hora}")
                self.lbl_monto.config(text=money(apertura["monto_inicial"] or 0))
                self.btn_abrir.grid_remove()
                self.f_monto.grid()
                self.lbl_responsable.config(text=apertura["usuario"])
            else:
                self.lbl_estado_sub.config(
                    text="Todavía no se registró la apertura de esta caja")
                self.f_monto.grid_remove()
                self.btn_abrir.grid()
                self.btn_abrir.configurar_estado(
                    True, texto=f"Abrir caja — {usuario}", color=st.VERDE)
                self.lbl_responsable.config(text=usuario)

            if db.puede("cerrar_caja"):
                self.btn_cierre.configurar_estado(
                    True, texto=f"Cerrar caja — {usuario}", color=AZUL)
            else:
                self.btn_cierre.configurar_estado(
                    False, texto="Sin permisos para cerrar")

            self.lbl_pie.config(
                text="Al finalizar la jornada, revisá el resumen del día, "
                     "contá los billetes y confirmá el cierre.")
        else:
            self.btn_abrir.grid_remove()
            self.f_monto.grid_remove()
            # Caja cerrada: ofrecer reabrirla directamente desde acá.
            if db.puede("reabrir_caja"):
                self.btn_reabrir.grid()
                self.btn_reabrir.configurar_estado(
                    True, texto=f"Reabrir caja — {usuario}", color=st.ROJO)
                self.lbl_estado_sub.config(
                    text="Esta caja está cerrada. Reabrirla si necesitás "
                         "modificarla.")
            else:
                self.btn_reabrir.grid_remove()
                self.lbl_estado_sub.config(
                    text="Esta caja ya fue cerrada y está bloqueada")
            self.btn_cierre.configurar_estado(
                False, texto="Caja cerrada — bloqueada")
            self.lbl_responsable.config(text=usuario)
            cierre = db.get_cierre_activo(caja["id"])
            if cierre:
                self.lbl_pie.config(
                    text=(
                        f"Cierre del {fecha_corta(cierre['fecha'])} a las "
                        f"{cierre['hora_cierre']} — Total vendido "
                        f"{money(cierre['total_vendido'])} — Diferencia "
                        f"{money(cierre['diferencia'])} — Estado: "
                        f"{cierre['estado']}. La caja está bloqueada."))

        # ---- Resumen ----
        r = db.resumen(caja["id"])
        tarj = r["debito"] + r["credito"]
        tg = float(r["total_general"] or 0)

        def pct(v):
            v = float(v or 0)
            return f"{round(v / tg * 100)}% del total" if tg > 0 and v > 0 \
                else "Sin movimientos"

        self.v_total.config(text=money(r["total_vendido"]))
        self.v_garrafas.config(text=str(r["total_garrafas"]))
        self.v_cantidad.config(text=str(r["cantidad_ventas"]))
        self.v_efectivo.config(text=money(r["efectivo"]))
        self.d_efectivo.config(text=pct(r["efectivo"]))
        self.v_transf.config(text=money(r["transferencias"]))
        self.d_transf.config(text=pct(r["transferencias"]))
        self.v_tarjetas.config(text=money(tarj))
        self.d_tarjetas.config(
            text=f"Débito {money(r['debito'])}  ·  Crédito {money(r['credito'])}")
        self.v_general.config(text=money(r["total_general"]))

        # ---- Ventas por producto ----
        for w in self.contenedor_producto.winfo_children():
            w.destroy()
        vendidos = [(pid, info) for pid, info in r["por_producto"].items()
                    if int(info["cantidad"]) > 0]
        if not vendidos:
            self._pintar_vacio()
        else:
            self._pintar_productos(vendidos)

    def _pintar_vacio(self):
        cont = self.contenedor_producto
        centro = tk.Frame(cont, bg=st.TARJETA)
        centro.pack(expand=True, pady=18)
        tk.Label(centro, image=ic.cuadro("boxopen", 58, GRIS_ICONO, GRIS_CLARO,
                                         14, 28, 1.6),
                 bg=st.TARJETA).pack()
        _lbl(centro, "Todavía no se vendió nada en esta caja.", 12,
             st.TEXTO, True).pack(pady=(14, 4))
        _lbl(centro, "El detalle por producto aparecerá al registrar una venta.",
             10, MUTED).pack()

    def _pintar_productos(self, vendidos):
        cont = self.contenedor_producto
        cont.columnconfigure(0, weight=1)
        for j, (txt, anc) in enumerate((("PRODUCTO", "w"), ("UNIDADES", "e"),
                                        ("TOTAL", "e"))):
            tk.Label(cont, text=txt, bg=st.TARJETA, fg=MUTED, anchor=anc,
                     font=(st.FUENTE, 8, "bold"), width=0 if j == 0 else 14
                     ).grid(row=0, column=j, sticky="ew", pady=(0, 6))
        fila = 1
        for _pid, info in vendidos:
            tk.Label(cont, text=info["nombre"], bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 11), anchor="w"
                     ).grid(row=fila, column=0, sticky="ew", pady=3)
            tk.Label(cont, text=f"{info['cantidad']} u.", bg=st.TARJETA,
                     fg=MUTED, font=(st.FUENTE, 10), anchor="e", width=14
                     ).grid(row=fila, column=1, sticky="e")
            tk.Label(cont, text=money(info["total"]), bg=st.TARJETA,
                     fg=st.TEXTO, font=(st.FUENTE, 11, "bold"), anchor="e",
                     width=14).grid(row=fila, column=2, sticky="e")
            fila += 1
        tk.Frame(cont, bg=st.BORDE, height=1).grid(
            row=fila, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        unidades_t = sum(int(i["cantidad"]) for _p, i in vendidos)
        dinero_t = sum(float(i["total"]) for _p, i in vendidos)
        tk.Label(cont, text="TOTAL GENERAL", bg=st.TARJETA, fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold"), anchor="w"
                 ).grid(row=fila + 1, column=0, sticky="ew")
        tk.Label(cont, text=f"{unidades_t} u.", bg=st.TARJETA,
                 fg=st.VERDE_OSCURO, font=(st.FUENTE, 10, "bold"), anchor="e",
                 width=14).grid(row=fila + 1, column=1, sticky="e")
        tk.Label(cont, text=money(dinero_t), bg=st.TARJETA, fg=st.VERDE_OSCURO,
                 font=(st.FUENTE, 11, "bold"), anchor="e", width=14
                 ).grid(row=fila + 1, column=2, sticky="e")


class AbrirCajaDialog(tk.Toplevel):
    """Diálogo para abrir la caja del día registrando el monto inicial."""

    def __init__(self, master, caja, on_abierto=None):
        super().__init__(master)
        self.caja = caja
        self.on_abierto = on_abierto
        self.title("Abrir caja")
        self.configure(bg=st.BARRA)
        self.resizable(False, False)
        # Modal: queda siempre encima de la ventana principal y toma el foco.
        # Sin esto, en el .exe compilado el diálogo podía abrirse DETRÁS de la
        # ventana principal y el usuario creía que el botón no hacía nada.
        self.transient(master)
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
        # Toma el input (modal real) y se asegura de quedar visible arriba.
        try:
            self.grab_set()
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass

    def _cancelar(self):
        self.destroy()

    def _abrir(self):
        # parse_numero entiende el formato argentino: "15.500,75", "$20.000", "1000"
        monto = parse_numero(self.var.get())
        if monto is None or monto < 0:
            messagebox.showerror("Monto inválido",
                                 "Ingresá un monto inicial válido.",
                                 parent=self)
            return
        try:
            db.registrar_apertura(self.caja["id"], monto)
        except Exception as e:
            errores.mostrar(
                "No se pudo abrir la caja", e, parent=self,
                contexto="registrar apertura de caja",
                mensaje="No se pudo registrar la apertura de la caja.\n"
                        "Los datos cargados se conservan; probá de nuevo.")
            return
        if self.on_abierto:
            self.on_abierto()
        self.destroy()
