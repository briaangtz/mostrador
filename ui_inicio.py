# -*- coding: utf-8 -*-
"""Panel principal: CAJA DEL DÍA."""

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

    def _construir(self):
        # Con scroll vertical: el listado de productos crece con la cantidad
        # de productos y en pantallas chicas nada queda cortado.
        # (App._rueda_global detecta este canvas_scroll automáticamente.)
        contenido = st.contenido_scrollable(self)

        # ---------------- Cabecera ----------------
        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 4))
        self.cab = cab

        izq = tk.Frame(cab, bg=st.FONDO)
        izq.pack(side="left")
        tk.Label(izq, text="CAJA DEL DÍA", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        self.lbl_fecha_larga = tk.Label(izq, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                        font=(st.FUENTE, 11))
        self.lbl_fecha_larga.pack(anchor="w")

        der = tk.Frame(cab, bg=st.FONDO)
        der.pack(side="right")
        tk.Label(der, text="Ver caja de la fecha:", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 9)).pack(anchor="e")
        self.combo_cajas = ttk.Combobox(der, state="readonly", width=22,
                                        font=(st.FUENTE, 10))
        self.combo_cajas.pack(anchor="e", pady=(2, 0))
        self.combo_cajas.bind("<<ComboboxSelected>>", self._seleccionar_caja)
        self._cajas_mapa = []

        # ---------------- Aviso de cajas sin cerrar ----------------
        self.banner = tk.Frame(contenido, bg=st.AMBAR_CLARO,
                               highlightbackground=st.AMBAR, highlightthickness=1)
        self.lbl_banner = tk.Label(self.banner, text="", bg=st.AMBAR_CLARO,
                                   fg=st.TEXTO, font=(st.FUENTE, 10), anchor="w",
                                   padx=12, pady=8)
        self.lbl_banner.pack(side="left", fill="x", expand=True)
        self.btn_banner = tk.Button(self.banner, text="Abrir y cerrar",
                                    command=self._abrir_pendiente, relief="flat",
                                    bg=st.AMBAR, fg="#ffffff",
                                    font=(st.FUENTE, 9, "bold"), padx=12, pady=6,
                                    cursor="hand2")

        # ---------------- Estado de la caja ----------------
        # Se empaquetan acá (y no al refrescar) para que aparezcan siempre
        # debajo de la cabecera y nunca queden ocultos.
        self.lbl_estado_caja = tk.Label(contenido, text="", bg=st.FONDO,
                                        font=(st.FUENTE, 11, "bold"), anchor="w")
        self.lbl_estado_caja.pack(fill="x", padx=24, pady=(10, 0))

        # Quién abrió la caja (trazabilidad)
        self.lbl_apertura = tk.Label(contenido, text="", bg=st.FONDO,
                                     fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9),
                                     anchor="w")
        self.lbl_apertura.pack(fill="x", padx=24, pady=(2, 0))

        # ---------------- Tarjetas ----------------
        marco_cards = tk.Frame(contenido, bg=st.FONDO)
        marco_cards.pack(fill="x", padx=24, pady=(8, 0))
        self.marco_cards = marco_cards

        self.cards = {}
        self.cards_detalle = {}
        definiciones = [
            ("Garrafas vendidas", "garrafas", 1),
            ("Total vendido", "total", 1),
            ("Efectivo", "efectivo", 1),
            ("Transferencias", "transferencia", 1),
            ("Tarjetas", "tarjetas", 2),
            ("Total general", "general", 1),
            ("Ventas registradas", "cantidad", 1),
        ]
        fila, col = 0, 0
        for titulo, clave, span in definiciones:
            if col + span > 4:
                fila, col = fila + 1, 0
            celda = tk.Frame(marco_cards, bg=st.FONDO)
            celda.grid(row=fila, column=col, columnspan=span,
                       sticky="nsew", padx=6, pady=4)
            frame, lbl = st.tarjeta(celda, titulo, ancho_chico=True)
            frame.pack(fill="both", expand=True)
            lbl.config(height=1)
            self.cards[clave] = lbl
            self.cards_detalle[clave] = frame.lbl_detalle
            col += span
        for c in range(4):
            marco_cards.columnconfigure(c, weight=1)

        self.cards["general"].config(fg=st.VERDE_OSCURO)

        # ---------------- Botones de apertura y cierre ----------------
        marco_accion = tk.Frame(contenido, bg=st.FONDO)
        marco_accion.pack(fill="x", padx=24, pady=(18, 0))

        self.btn_abrir = tk.Button(
            marco_accion,
            text="ABRIR CAJA",
            command=self._abrir_caja,
            relief="flat",
            bg=st.VERDE,
            fg="#ffffff",
            font=(st.FUENTE, 14, "bold"),
            pady=16,
            cursor="hand2",
        )
        self.btn_abrir.pack(side="left", fill="x", expand=True)
        self.btn_abrir.bind("<Enter>",
                            lambda e: self.btn_abrir.config(bg=st.VERDE_OSCURO))
        self.btn_abrir.bind("<Leave>",
                            lambda e: self.btn_abrir.config(bg=st.VERDE))

        self.btn_cierre = tk.Button(
            marco_accion,
            text="CERRAR CAJA",
            command=self._abrir_cierre,
            relief="flat",
            bg=st.ACENTO,
            fg="#ffffff",
            font=(st.FUENTE, 14, "bold"),
            pady=16,
            cursor="hand2",
        )
        self.btn_cierre.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.btn_cierre.bind("<Enter>",
                             lambda e: self.btn_cierre.config(bg=st.ACENTO_OSCURO))
        self.btn_cierre.bind("<Leave>",
                             lambda e: self.btn_cierre.config(bg=st.ACENTO))

        self.lbl_detalle_cierre = tk.Label(contenido, text="", bg=st.FONDO,
                                           fg=st.TEXTO_SUAVE,
                                           font=(st.FUENTE, 10), anchor="w")
        self.lbl_detalle_cierre.pack(fill="x", padx=24, pady=(8, 0))

        # ---------------- Resumen por producto ----------------
        marco_prod = st.labelframe(contenido, " VENTAS POR PRODUCTO ",
                                   padx=14, pady=10)
        marco_prod.pack(fill="x", padx=24, pady=(18, 24))

        self.filas_producto = {}
        self.contenedor_producto = tk.Frame(marco_prod, bg=st.FONDO)
        self.contenedor_producto.pack(fill="x")

    # ------------------------------------------------------------- acciones
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

    def _abrir_caja(self):
        if not db.puede("abrir_caja"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no tiene permiso para abrir cajas.",
                                 parent=self)
            return
        caja = self.app.caja_actual()
        if not caja:
            return
        if caja["estado"] != "abierta":
            messagebox.showinfo(
                "Caja cerrada",
                "Esta caja ya fue cerrada y está bloqueada.",
                parent=self,
            )
            return
        apertura = db.apertura_de(caja["id"])
        if apertura:
            messagebox.showinfo(
                "Caja ya abierta",
                f"Esta caja ya fue abierta por {apertura['usuario']} "
                f"a las {(apertura['hora'] or '')[:5]}.",
                parent=self,
            )
            return
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
                parent=self,
            )
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
                parent=self,
            ):
                return
            fondo = float(r.get("fondo") or 0)
            try:
                db.guardar_cierre(
                    caja["id"],
                    total_garrafas=0, total_vendido=0,
                    efectivo_esperado=fondo, efectivo_contado=fondo,
                    transferencias=0, debito=0, credito=0, bono=0, total_general=0,
                    diferencia=0, estado="Cuadrada",
                    billetes={}, n_transferencias=0,
                )
            except Exception as e:
                messagebox.showerror("No se pudo cerrar", str(e), parent=self)
                return
            try:
                db.respaldar("cierre de caja")
            except Exception:
                pass
            # Sin ventanas de más: el resultado se ve en esta misma pantalla
            # (■ CAJA CERRADA + detalle del cierre registrado).
            self.app.refrescar_todo()
            return

        # -------- Con ventas: arqueo completo (diálogo + contraseña) --------
        def al_cerrar():
            self.app.refrescar_todo()
            # Vuelta automática a la pantalla de Inicio con el cierre visible
            self.app.mostrar("inicio")

        CierreDialog(self.app, caja, on_cerrado=al_cerrar)

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
        pendientes = [c for c in db.cajas_abiertas() if c["fecha"] != fecha]
        if pendientes:
            fechas = ", ".join(fecha_corta(c["fecha"]) for c in pendientes)
            self.lbl_banner.config(
                text=f"⚠ Hay cajas sin cerrar de otro día: {fechas}. "
                     f"Deben cerrarse para no mezclar los datos."
            )
            self.btn_banner.pack(side="right", padx=10, pady=6)
        else:
            self.banner.pack_forget()

        if pendientes:
            # Siempre justo debajo de la cabecera, sin importar cuántas veces
            # se muestre u oculte.
            self.banner.pack(fill="x", padx=24, pady=(12, 0), after=self.cab)

        # Resumen
        r = db.resumen(caja["id"])
        self.cards["garrafas"].config(text=str(r["total_garrafas"]))
        self.cards["total"].config(text=money(r["total_vendido"]))
        self.cards["efectivo"].config(text=money(r["efectivo"]))
        self.cards["transferencia"].config(text=money(r["transferencias"]))
        self.cards["tarjetas"].config(text=money(r["debito"] + r["credito"]))
        self.cards_detalle["tarjetas"].config(
            text=f"Débito {money(r['debito'])}  •  Crédito {money(r['credito'])}"
        )
        self.cards["general"].config(text=money(r["total_general"]))
        self.cards["cantidad"].config(text=str(r["cantidad_ventas"]))

        # Estado de los botones de apertura y cierre
        cierre = db.get_cierre_activo(caja["id"])
        usuario_txt = self._usuario_txt()
        if caja["estado"] == "abierta":
            self.lbl_estado_caja.config(text="● CAJA ABIERTA", fg=st.VERDE_OSCURO)
            self.lbl_estado_caja.pack(fill="x", padx=24, pady=(10, 0),
                                      before=self.marco_cards)

            # Quién abrió esta caja y con cuánto fondo inicial
            apertura = db.apertura_de(caja["id"])
            if apertura:
                self.lbl_apertura.config(
                    text=f"Abierta por {apertura['usuario']} a las "
                         f"{(apertura['hora'] or '')[:5]} — monto inicial "
                         f"{money(apertura['monto_inicial'] or 0)}"
                )
            else:
                self.lbl_apertura.config(
                    text="Sin apertura registrada — presioná ABRIR CAJA "
                         "para registrar quién la abre y con cuánto fondo."
                )
            self.lbl_apertura.pack(fill="x", padx=24, pady=(2, 0),
                                   before=self.marco_cards)

            # Botón ABRIR: solo si todavía no se registró la apertura
            if apertura:
                self.btn_abrir.config(
                    state="disabled", bg="#a3d9b5",
                    text=f"CAJA ABIERTA — {apertura['usuario']} "
                         f"{(apertura['hora'] or '')[:5]}"
                )
            elif db.puede("abrir_caja"):
                self.btn_abrir.config(state="normal", bg=st.VERDE,
                                      text=f"ABRIR CAJA — {usuario_txt}")
            else:
                self.btn_abrir.config(state="disabled", bg="#a3d9b5",
                                      text="SIN PERMISOS PARA ABRIR")

            # Botón CERRAR
            if db.puede("cerrar_caja"):
                self.btn_cierre.config(state="normal", bg=st.ACENTO,
                                       text=f"CERRAR CAJA — {usuario_txt}")
            else:
                self.btn_cierre.config(state="disabled", bg="#9db7ee",
                                       text="SIN PERMISOS PARA CERRAR")
            if cierre:
                self.lbl_detalle_cierre.config(text="")
            else:
                self.lbl_detalle_cierre.config(
                    text="Al finalizar la jornada presioná el botón, revisá el resumen "
                         "del día, contá los billetes y confirmá el cierre."
                )
        else:
            self.lbl_estado_caja.config(text="■ CAJA CERRADA", fg=st.ROJO)
            self.lbl_estado_caja.pack(fill="x", padx=24, pady=(10, 0),
                                      before=self.marco_cards)
            self.lbl_apertura.pack_forget()
            self.btn_abrir.config(state="disabled", bg="#a3d9b5",
                                  text="CAJA CERRADA")
            self.btn_cierre.config(state="disabled", bg="#9db7ee",
                                   text="CAJA CERRADA — BLOQUEADA")
            if cierre:
                estado = cierre["estado"]
                self.lbl_detalle_cierre.config(
                    text=(
                        f"Cierre del {fecha_corta(cierre['fecha'])} a las "
                        f"{cierre['hora_cierre']} — Total vendido "
                        f"{money(cierre['total_vendido'])} — Diferencia "
                        f"{money(cierre['diferencia'])} — Estado: {estado}. "
                        f"La caja está bloqueada."
                    ),
                    fg=st.TEXTO_SUAVE,
                )

        # Ventas por producto: solo lo que se vendió, con su total general
        for w in self.contenedor_producto.winfo_children():
            w.destroy()
        self.filas_producto = {}
        vendidos = [(pid, info) for pid, info in r["por_producto"].items()
                    if int(info["cantidad"]) > 0]
        if not vendidos:
            tk.Label(self.contenedor_producto,
                     text=("Sin productos configurados."
                           if not r["por_producto"]
                           else "Todavía no se vendió nada en esta caja."),
                     bg=st.FONDO, fg=st.TEXTO_SUAVE).pack(anchor="w")
        for pid, info in vendidos:
            fila = tk.Frame(self.contenedor_producto, bg=st.FONDO)
            fila.pack(fill="x", pady=2)
            tk.Label(fila, text=f"• {info['nombre']}", bg=st.FONDO, fg=st.TEXTO,
                     font=(st.FUENTE, 11), anchor="w").pack(side="left")
            tk.Label(fila, text=f"{info['cantidad']} unidades", bg=st.FONDO,
                     fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10),
                     anchor="e").pack(side="right", padx=(0, 20))
            tk.Label(fila, text=money(info["total"]), bg=st.FONDO, fg=st.TEXTO,
                     font=(st.FUENTE, 11, "bold"), width=14, anchor="e").pack(
                side="right")

        # Total general: la suma de todas las unidades y de todo el dinero
        if vendidos:
            unidades_t = sum(int(info["cantidad"]) for _pid, info in vendidos)
            dinero_t = sum(float(info["total"]) for _pid, info in vendidos)
            tk.Frame(self.contenedor_producto, bg=st.BARRA, height=2).pack(
                fill="x", pady=(8, 4))
            total = tk.Frame(self.contenedor_producto, bg=st.FONDO)
            total.pack(fill="x")
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

        ancho, alto = 430, 330
        self.geometry(f"{ancho}x{alto}")
        self.update_idletasks()
        x = max(0, (self.winfo_screenwidth() - ancho) // 2)
        y = max(0, (self.winfo_screenheight() - alto) // 2 - 40)
        self.geometry(f"+{x}+{y}")

        cont = tk.Frame(self, bg=st.BARRA)
        cont.pack(fill="both", expand=True, padx=32, pady=(26, 24))

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
                       relief="solid", bd=1)
        ent.pack(fill="x", pady=(4, 8), ipady=6)
        ent.focus_set()
        ent.select_range(0, "end")

        tk.Label(cont,
                 text="Efectivo con el que empezás el día. Se registra con tu "
                      "usuario y la hora de apertura.",
                 bg=st.BARRA, fg="#9fb0cc", font=(st.FUENTE, 8),
                 justify="left").pack(anchor="w", pady=(0, 14))

        self.lbl_error = tk.Label(cont, text="", bg=st.BARRA, fg="#fca5a5",
                                  font=(st.FUENTE, 9), anchor="w", justify="left")
        self.lbl_error.pack(fill="x")

        fila = tk.Frame(cont, bg=st.BARRA)
        fila.pack(fill="x", pady=(14, 0))

        tk.Button(fila, text="CANCELAR", command=self._cancelar,
                  relief="flat", bg="#3b4a6b", fg="#ffffff",
                  font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
                  cursor="hand2").pack(side="left", fill="x", expand=True)
        btnAbrir = tk.Button(fila, text="ABRIR CAJA", command=self._confirmar,
                             relief="flat", bg=st.VERDE, fg="#ffffff",
                             font=(st.FUENTE, 11, "bold"), padx=18, pady=11,
                             cursor="hand2")
        btnAbrir.pack(side="left", fill="x", expand=True, padx=(10, 0))
        btnAbrir.bind("<Enter>", lambda e: btnAbrir.config(bg=st.VERDE_OSCURO))
        btnAbrir.bind("<Leave>", lambda e: btnAbrir.config(bg=st.VERDE))

        self.bind("<Return>", lambda e: self._confirmar())
        self.bind("<Escape>", lambda e: self._cancelar())
        try:
            self.transient(master)
        except tk.TclError:
            pass
        self.grab_set()

    def _confirmar(self):
        texto = (self.var.get().replace("$", "").replace(" ", "")
                 .replace(".", "").replace(",", "."))
        try:
            monto = float(texto)
        except ValueError:
            self.lbl_error.config(
                text="Ingresá un importe numérico. Ejemplos: 50000 o 50.000")
            return
        if monto < 0:
            self.lbl_error.config(text="El monto no puede ser negativo.")
            return
        try:
            db.abrir_caja(self.caja["id"], monto)
        except ValueError as e:
            self.lbl_error.config(text=str(e))
            return
        u = db.usuario_sesion()
        messagebox.showinfo(
            "Caja abierta",
            f"Caja del {db.fecha_larga(self.caja['fecha'])} abierta.\n\n"
            f"Responsable: {u['usuario'] if u else '—'}\n"
            f"Monto inicial: {money(monto)}",
            parent=self,
        )
        self.destroy()
        if self.on_abierto:
            self.on_abierto()

    def _cancelar(self):
        self.destroy()
