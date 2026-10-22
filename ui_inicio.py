# -*- coding: utf-8 -*-
"""Panel principal: MOSTRADOR (Caja del día)."""

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
        # Con scroll vertical para pantallas chicas.
        contenido = st.contenido_scrollable(self)

        # ---------------- Cabecera ----------------
        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 10))
        self.cab = cab

        izq = tk.Frame(cab, bg=st.FONDO)
        izq.pack(side="left")
        tk.Label(izq, text="MOSTRADOR", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 26, "bold")).pack(anchor="w")
        self.lbl_fecha_larga = tk.Label(izq, text="", bg=st.FONDO,
                                        fg=st.TEXTO_SUAVE, font=(st.FUENTE, 12))
        self.lbl_fecha_larga.pack(anchor="w")
        self.lbl_estado_caja = tk.Label(izq, text="● CAJA ABIERTA",
                                        bg=st.FONDO, fg=st.VERDE,
                                        font=(st.FUENTE, 10, "bold"))
        self.lbl_estado_caja.pack(anchor="w", pady=(2, 0))

        der = tk.Frame(cab, bg=st.FONDO)
        der.pack(side="right")
        tk.Label(der, text="Ver caja de la fecha:", bg=st.FONDO,
                 fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9)).pack(anchor="e")
        self.combo_cajas = ttk.Combobox(der, state="readonly", width=22,
                                        font=(st.FUENTE, 10))
        self.combo_cajas.pack(anchor="e", pady=(2, 0))
        self.combo_cajas.bind("<<ComboboxSelected>>", self._seleccionar_caja)
        self._cajas_mapa = []

        # ---------------- Aviso de cajas sin cerrar ----------------
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

        # ---------------- Cards de resumen ----------------
        tarjetas_fila = tk.Frame(contenido, bg=st.FONDO)
        tarjetas_fila.pack(fill="x", padx=24, pady=(18, 6))

        definiciones = [
            ("GARRAFAS VENDIDAS", "garrafas", st.COLOR_GARRAFA,
             lambda r: str(r["total_garrafas"])),
            ("TOTAL VENDIDO", "total", st.COLOR_TOTAL,
             lambda r: money(r["total_vendido"])),
            ("EFECTIVO", "efectivo", st.COLOR_EFECTIVO,
             lambda r: money(r["efectivo"])),
            ("TRANSFERENCIAS", "transferencia", st.COLOR_TRANS,
             lambda r: money(r["transferencias"])),
            ("TARJETAS", "tarjetas", st.COLOR_TARJETA,
             lambda r: money(r["debito"] + r["credito"])),
            ("TOTAL GENERAL", "general", st.COLOR_TOTAL,
             lambda r: money(r["total_general"])),
            ("VENTAS REGISTRADAS", "cantidad", st.COLOR_VENTAS,
             lambda r: str(r["cantidad_ventas"])),
        ]

        self.cards = {}
        self.cards_detalle = {}
        for i, (titulo, clave, color, valor_fn) in enumerate(definiciones):
            celda = tk.Frame(tarjetas_fila, bg=st.FONDO)
            celda.pack(side="left", fill="both", expand=True, padx=6, pady=4)
            frame, lbl_v = st.tarjeta(
                celda, titulo, "—", color=color, fuente_valor=18)
            frame.pack(fill="both", expand=True)
            self.cards[clave] = lbl_v
            self.cards_detalle[clave] = frame.lbl_detalle

        # ---------------- Botones de acción ----------------
        marco_accion = tk.Frame(contenido, bg=st.FONDO)
        marco_accion.pack(fill="x", padx=24, pady=(18, 0))

        self.btn_abrir = tk.Button(
            marco_accion, text="CAJA ABIERTA — Usuario",
            command=self._abrir_caja, relief="flat", bd=0,
            bg=st.VERDE, fg="#ffffff",
            font=(st.FUENTE, 14, "bold"), pady=14, cursor="hand2")
        self.btn_abrir.pack(side="left", fill="x", expand=True,
                            padx=(0, 12))
        self.btn_abrir.bind(
            "<Enter>", lambda e: self.btn_abrir.config(bg=st.VERDE_OSCURO))
        self.btn_abrir.bind(
            "<Leave>", lambda e: self.btn_abrir.config(bg=st.VERDE))

        self.btn_cierre = tk.Button(
            marco_accion, text="CERRAR CAJA — Usuario",
            command=self._abrir_cierre, relief="flat", bd=0,
            bg=st.ACENTO, fg="#ffffff",
            font=(st.FUENTE, 14, "bold"), pady=14, cursor="hand2")
        self.btn_cierre.pack(side="left", fill="x", expand=True,
                             padx=(12, 0))
        self.btn_cierre.bind(
            "<Enter>", lambda e: self.btn_cierre.config(bg=st.ACENTO_OSCURO))
        self.btn_cierre.bind(
            "<Leave>", lambda e: self.btn_cierre.config(bg=st.ACENTO))

        # ---------------- Pie de ayuda ----------------
        self.lbl_pie = tk.Label(
            contenido,
            text="Al finalizar la jornada presioná CERRAR CAJA, revisá el resumen del día, "
                 "contá los billetes y confirmá el cierre.",
            bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10),
            wraplength=880, anchor="w", justify="left")
        self.lbl_pie.pack(fill="x", padx=24, pady=(12, 20))

        # ---------------- Ventas por producto ----------------
        marco_prod = st.labelframe(contenido, " VENTAS POR PRODUCTO ",
                                   padx=14, pady=10)
        marco_prod.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.contenedor_producto = tk.Frame(marco_prod, bg=st.FONDO)
        self.contenedor_producto.pack(fill="both", expand=True)

        self.filas_producto = {}

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
        from ui_inicio import AbrirCajaDialog  # import local para evitar ciclo
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

    def _seleccionar_caja(self, _=None):
        idx = self.combo_cajas.current()
        if idx < 0 or idx >= len(self._cajas_mapa):
            return
        fecha = self._cajas_mapa[idx]
        self.app.cambiar_caja(fecha)

    def _abrir_pendiente(self):
        pendientes = [c for c in db.cajas_abiertas()
                      if c["fecha"] != self.app.caja_fecha]
        if pendientes:
            self.app.cambiar_caja(pendientes[0]["fecha"])

    def _usuario_txt(self):
        u = db.usuario_sesion()
        return u["usuario"] if u else "—"

    # ------------------------------------------------------------- refresco
    def refresh(self):
        caja = self.app.caja_actual()
        if not caja:
            return

        fecha = caja["fecha"]
        self.lbl_fecha_larga.config(text=fecha_larga(fecha))

        # Combo de selección de caja
        cajas = db.todas_las_cajas()
        etiquetas = []
        self._cajas_mapa = []
        for c in cajas:
            marca = "✓ cerrada" if c["estado"] == "cerrada" else "• abierta"
            etiquetas.append(f"{fecha_corta(c['fecha'])}  ({marca})")
            self._cajas_mapa.append(c["fecha"])
        self.combo_cajas["values"] = etiquetas
        if fecha in self._cajas_mapa:
            self.combo_cajas.current(self._cajas_mapa.index(fecha))

        # Banner de cajas anteriores sin cerrar
        pendientes = [c for c in db.cajas_abiertas()
                      if c["fecha"] != fecha]
        if pendientes:
            fechas = ", ".join(fecha_corta(c["fecha"]) for c in pendientes)
            self.lbl_banner.config(
                text=f"⚠ Hay cajas sin cerrar de otro día: {fechas}. "
                     f"Deben cerrarse para no mezclar los datos.")
            self.btn_banner.pack(side="right", padx=10, pady=6)
        else:
            self.btn_banner.pack_forget()
            self.banner.pack_forget()

        if pendientes:
            self.banner.pack(fill="x", padx=24, pady=(12, 0), after=self.cab)

        # Resumen en cards
        r = db.resumen(caja["id"])
        self.cards["garrafas"].config(text=str(r["total_garrafas"]))
        self.cards["total"].config(text=money(r["total_vendido"]))
        self.cards["efectivo"].config(text=money(r["efectivo"]))
        self.cards["transferencia"].config(text=money(r["transferencias"]))
        self.cards["tarjetas"].config(
            text=money(r["debito"] + r["credito"]))
        self.cards_detalle["tarjetas"].config(
            text=f"Débito {money(r['debito'])}  •  Crédito {money(r['credito'])}")
        self.cards["general"].config(text=money(r["total_general"]))
        self.cards["cantidad"].config(text=str(r["cantidad_ventas"]))

        # Estado de los botones de apertura y cierre
        cierre = db.get_cierre_activo(caja["id"])
        usuario_txt = self._usuario_txt()
        if caja["estado"] == "abierta":
            self.lbl_estado_caja.config(text="● CAJA ABIERTA",
                                        fg=st.VERDE)
            apertura = db.apertura_de(caja["id"])
            if apertura:
                self.btn_abrir.config(
                    state="disabled", bg="#a3d9b5",
                    text=f"CAJA ABIERTA — {apertura['usuario']} "
                         f"{(apertura['hora'] or '')[:5]}")
            elif db.puede("abrir_caja"):
                self.btn_abrir.config(state="normal", bg=st.VERDE,
                                      text=f"ABRIR CAJA — {usuario_txt}")
            else:
                self.btn_abrir.config(state="disabled", bg="#a3d9b5",
                                      text="SIN PERMISOS PARA ABRIR")

            if db.puede("cerrar_caja"):
                self.btn_cierre.config(state="normal", bg=st.ACENTO,
                                       text=f"CERRAR CAJA — {usuario_txt}")
            else:
                self.btn_cierre.config(state="disabled", bg="#9db7ee",
                                       text="SIN PERMISOS PARA CERRAR")
            if cierre:
                self.lbl_pie.config(text="")
            else:
                self.lbl_pie.config(
                    text="Al finalizar la jornada presioná CERRAR CAJA, revisá el "
                         "resumen del día, contá los billetes y confirmá el cierre.")
        else:
            self.lbl_estado_caja.config(text="■ CAJA CERRADA", fg=st.ROJO)
            self.btn_abrir.config(state="disabled", bg="#a3d9b5",
                                  text="CAJA CERRADA")
            self.btn_cierre.config(state="disabled", bg="#9db7ee",
                                   text="CAJA CERRADA — BLOQUEADA")
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

        # Ventas por producto: solo lo que se vendió
        for w in self.contenedor_producto.winfo_children():
            w.destroy()
        vendidos = [(pid, info) for pid, info in r["por_producto"].items()
                    if int(info["cantidad"]) > 0]
        if not vendidos:
            tk.Label(self.contenedor_producto,
                     text="Todavía no se vendió nada en esta caja.",
                     bg=st.FONDO, fg=st.TEXTO_SUAVE,
                     font=(st.FUENTE, 11)).pack(anchor="w")
        else:
            self.lbl_sin_ventas.pack_forget()
            for pid, info in vendidos:
                fila = tk.Frame(self.contenedor_producto, bg=st.FONDO)
                fila.pack(fill="x", pady=2)
                tk.Label(fila, text=f"• {info['nombre']}", bg=st.FONDO,
                         fg=st.TEXTO, font=(st.FUENTE, 11),
                         anchor="w").pack(side="left")
                tk.Label(fila, text=f"{info['cantidad']} unidades",
                         bg=st.FONDO, fg=st.TEXTO_SUAVE,
                         font=(st.FUENTE, 10),
                         anchor="e").pack(side="right", padx=(0, 20))
                tk.Label(fila, text=money(info["total"]), bg=st.FONDO,
                         fg=st.TEXTO, font=(st.FUENTE, 11, "bold"),
                         width=14, anchor="e").pack(side="right")

            tk.Frame(self.contenedor_producto, bg=st.BARRA, height=1).pack(
                fill="x", pady=(8, 4))
            total = tk.Frame(self.contenedor_producto, bg=st.FONDO)
            total.pack(fill="x")
            unidades_t = sum(int(info["cantidad"]) for _pid, info in vendidos)
            dinero_t = sum(float(info["total"]) for _pid, info in vendidos)
            tk.Label(total, text="TOTAL GENERAL", bg=st.FONDO, fg=st.TEXTO,
                     font=(st.FUENTE, 12, "bold"), anchor="w").pack(side="left")
            tk.Label(total, text=f"{unidades_t} unidades", bg=st.FONDO,
                     fg=st.VERDE_OSCURO, font=(st.FUENTE, 11, "bold"),
                     anchor="e").pack(side="right", padx=(0, 20))
            tk.Label(total, text=money(dinero_t), bg=st.FONDO,
                     fg=st.VERDE_OSCURO, font=(st.FUENTE, 12, "bold"),
                     width=14, anchor="e").pack(side="right")


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
