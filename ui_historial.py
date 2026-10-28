# -*- coding: utf-8 -*-
"""Historial de cierres: consulta, detalle y reapertura de cajas."""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import estilos as st
import iconos as ic
from util import money, fecha_larga, fecha_corta
from widgets_figma import Tarjeta, Btn, Banda
from dialogos import pedir_password
import ui_comun as uc

AMBAR_TXT = "#B45309"          # ámbar legible sobre fondo blanco


class HistorialPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._cierres = []
        self._construir()

    def _construir(self):
        PX = 28
        # Contenido con scroll: nada queda cortado en pantallas chicas
        contenido = st.contenido_scrollable(self)

        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=PX, pady=(22, 6))
        tk.Label(cab, text="Historial de cierres", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        sub = tk.Label(cab, text="Cierres de días anteriores. Cualquier usuario "
                                 "puede ver el detalle; la reapertura de una "
                                 "caja es una función de DESARROLLADOR con "
                                 "contraseña.",
                       bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 11),
                       wraplength=780, justify="left", anchor="w")
        sub.pack(anchor="w", fill="x", pady=(2, 0))
        cab.bind("<Configure>", lambda e: sub.configure(
            wraplength=max(300, e.width - 10)))

        # ---------------- Indicadores ----------------
        kpis = tk.Frame(contenido, bg=st.FONDO)
        kpis.pack(fill="x", padx=PX, pady=(14, 12))
        self.kpi_cierres = uc.kpi(kpis, 0, 3, "Cierres registrados", "history")
        self.kpi_vendido = uc.kpi(kpis, 1, 3, "Vendido acumulado", "dollar",
                                  uc.AZUL_I, uc.AZUL_F, borde="#C3D6F8")
        self.kpi_diferencias = uc.kpi(kpis, 2, 3, "Cierres con diferencia",
                                      "clipboard")

        # ---------------- Lista de cierres ----------------
        card, marco, enc = uc.tarjeta(contenido, "Cierres registrados", "history")
        card.pack(fill="both", expand=True, padx=PX)
        self.lbl_resumen = tk.Label(enc, text="", bg=st.TARJETA,
                                    fg=st.TEXTO_SUAVE, font=(st.FUENTE, 10))
        self.lbl_resumen.pack(side="right")

        zona = tk.Frame(marco, bg=st.TARJETA)
        zona.pack(fill="both", expand=True)
        columnas = ("fecha", "vendido", "efectivo", "transferencia", "tarjetas",
                    "diferencia", "estado")
        self.tree = ttk.Treeview(zona, columns=columnas, show="headings",
                                 height=12, selectmode="browse")
        encabezados = [
            ("fecha", "Fecha", 90, "center"),
            ("vendido", "Total vendido", 120, "e"),
            ("efectivo", "Efectivo", 110, "e"),
            ("transferencia", "Transferencia", 120, "e"),
            ("tarjetas", "Tarjetas", 140, "e"),
            ("diferencia", "Diferencia", 100, "e"),
            ("estado", "Estado", 95, "center"),
        ]
        for clave, texto, ancho, alinear in encabezados:
            self.tree.heading(clave, text=texto)
            self.tree.column(clave, width=ancho, anchor=alinear,
                             stretch=(clave in ("fecha", "estado")))

        scroll = ttk.Scrollbar(zona, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self._ver_detalle())

        pie = tk.Frame(marco, bg=st.TARJETA)
        pie.pack(fill="x", pady=(12, 0))
        self._btn(pie, "Ver detalle", st.ACENTO, self._ver_detalle).pack(side="left")
        self.btn_reabrir = self._btn(pie, "Reabrir caja (contraseña)", st.ROJO,
                                     self._reabrir)
        self.btn_reabrir.pack(side="left", padx=(10, 0))
        tk.Label(pie, text="Doble clic sobre un cierre para ver su detalle.",
                 bg=st.TARJETA, fg=st.TEXTO_SUAVE,
                 font=(st.FUENTE, 9)).pack(side="right")

        self.lbl_vacio = tk.Label(contenido,
                                  text="Todavía no hay cierres registrados.",
                                  bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                  font=(st.FUENTE, 11))
        tk.Frame(contenido, bg=st.FONDO, height=24).pack()

    def _btn(self, parent, texto, color, comando):
        return Btn(parent, text=texto, command=comando, bg=color, fg="#ffffff",
                   font=(st.FUENTE, 10, "bold"), padx=16, pady=9)

    # ------------------------------------------------------------- acciones
    def _seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Historial",
                                   "Seleccioná un cierre de la lista.", parent=self)
            return None
        return self._cierres[int(sel[0])]

    def _ver_detalle(self):
        cierre = self._seleccionado()
        if not cierre:
            return
        DetalleCierre(self.app, cierre)

    def _reabrir(self):
        # Validación interna de permisos (solo DESARROLLADOR)
        if not db.puede("reabrir_caja"):
            messagebox.showerror(
                "Sin permisos",
                "Solo un usuario con rango DESARROLLADOR puede reabrir cajas.",
                parent=self)
            return
        cierre = self._seleccionado()
        if not cierre:
            return

        u = db.usuario_sesion() or {}
        password = pedir_password(
            self, u.get("usuario", "—"), titulo="Reapertura de caja",
            mensaje="Ingresá TU contraseña para autorizar la reapertura:",
            subtitulo=f"Caja del {fecha_corta(cierre['fecha'])}")
        if password is None:
            return
        if not db.validar_password_sesion(password):
            messagebox.showerror("Reapertura denegada",
                                 "Contraseña incorrecta. La caja permanece cerrada.",
                                 parent=self)
            return

        if not messagebox.askyesno(
            "Reabrir caja",
            f"Se anulará el cierre del {fecha_corta(cierre['fecha'])} y la caja "
            f"volverá a quedar abierta para modificaciones.\n\n"
            "¿Continuar?",
            parent=self,
        ):
            return

        db.reabrir_caja(cierre["caja_id"])
        messagebox.showinfo("Caja reabierta",
                            "La caja fue reabierta. Ya podés modificar sus ventas "
                            "y volver a cerrarla.",
                            parent=self)
        self.app.cambiar_caja(cierre["fecha"])

    # ------------------------------------------------------------- refresco
    def refresh(self):
        # El botón de reapertura solo está disponible para DESARROLLADOR
        if db.puede("reabrir_caja"):
            self.btn_reabrir.config(state="normal", bg=st.ROJO)
        else:
            self.btn_reabrir.config(state="disabled", bg="#f0a8a8")

        self.tree.delete(*self.tree.get_children())
        self._cierres = db.historial_cierres()
        for i, c in enumerate(self._cierres):
            dif = c["diferencia"]
            self.tree.insert("", "end", iid=str(i), tags=(str(i),), values=(
                fecha_corta(c["fecha"]),
                money(c["total_vendido"]),
                money(c["efectivo_contado"]),
                money(c["transferencias"]),
                money(c["debito"] + c["credito"]),
                money(dif),
                c["estado"],
            ))
            if c["estado"] == "Faltante":
                self.tree.tag_configure(str(i), foreground=st.ROJO)
            elif c["estado"] == "Sobrante":
                self.tree.tag_configure(str(i), foreground=AMBAR_TXT)
            else:
                self.tree.tag_configure(str(i), foreground=st.VERDE_OSCURO)

        total = sum(c["total_vendido"] for c in self._cierres)
        con_dif = sum(1 for c in self._cierres
                      if c["estado"] in ("Faltante", "Sobrante"))
        self.kpi_cierres.config(text=str(len(self._cierres)))
        self.kpi_vendido.config(text=money(total))
        self.kpi_diferencias.config(text=str(con_dif))

        if self._cierres:
            self.lbl_vacio.pack_forget()
            self.lbl_resumen.config(
                text=f"{len(self._cierres)} cierre(s) — vendido acumulado: "
                     f"{money(total)}")
        else:
            self.lbl_vacio.pack(pady=30)
            self.lbl_resumen.config(text="")


class DetalleCierre(tk.Toplevel):
    """Detalle completo de un cierre."""

    def __init__(self, app, cierre):
        super().__init__(app)
        self.title(f"Detalle del cierre — {fecha_corta(cierre['fecha'])}")
        self.configure(bg=st.FONDO)

        # Se adapta al tamaño de la pantalla (nada cortado ni fuera de vista)
        uc.dimensionar(self, 1000, 820, 720, 520)
        self.transient(app)
        self.grab_set()

        # Botón fijo abajo
        fb = uc.pie_fijo(self)
        Btn(fb, text="Cerrar", command=self.destroy, bg="#E5EAF1", fg=st.TEXTO,
            font=(st.FUENTE, 10, "bold"), padx=26, pady=10).pack(side="right")

        # Contenido con scroll vertical (en pantallas chicas se baja con
        # la rueda del mouse y ningún dato queda oculto).
        self.canvas_scroll, pagina = uc.area_scroll(self)

        # ---------------- Título ----------------
        tk.Label(pagina, text="Detalle del cierre", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(pagina, text=f"Fecha: {fecha_larga(cierre['fecha'])}   —   "
                              f"Hora de cierre: {cierre['hora_cierre']}",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 11)
                 ).pack(anchor="w", pady=(2, 8))

        apertura = db.apertura_de(cierre["caja_id"])
        chip = Tarjeta(pagina, fondo=uc.AZUL_F, borde="#C3D6F8", radio=14,
                       padx=14, pady=7, ancho_auto=True)
        chip.pack(anchor="w")
        cf = tk.Frame(chip.cuerpo, bg=uc.AZUL_F)
        cf.pack()
        tk.Label(cf, image=ic.icono("user", 18, uc.AZUL_I, 1.8),
                 bg=uc.AZUL_F).pack(side="left", padx=(0, 8))
        tk.Label(
            cf,
            text=f"Abierta por: {apertura['usuario'] if apertura else '—'}"
                 f"   —   Cerrada por: "
                 f"{cierre.get('cerrado_por_nombre') or '(usuario eliminado)'}",
            bg=uc.AZUL_F, fg=st.ACENTO_OSCURO, font=(st.FUENTE, 10, "bold"),
        ).pack(side="left")

        # ---------------- Indicadores ----------------
        dif = cierre["diferencia"]
        estado = cierre["estado"]
        kpis = tk.Frame(pagina, bg=st.FONDO)
        kpis.pack(fill="x", pady=(14, 12))
        uc.kpi(kpis, 0, 3, "Garrafas vendidas", "cube",
               valor=str(cierre["total_garrafas"]))
        uc.kpi(kpis, 1, 3, "Total vendido", "dollar", uc.AZUL_I, uc.AZUL_F,
               borde="#C3D6F8", valor=money(cierre["total_vendido"]))
        uc.kpi(kpis, 2, 3, "Operaciones realizadas", "clipboard",
               valor=str(cierre.get("n_operaciones") or 0))

        # ---------------- Dos columnas ----------------
        cols = tk.Frame(pagina, bg=st.FONDO)
        cols.pack(fill="x")
        cols.columnconfigure(0, weight=1, uniform="col")
        cols.columnconfigure(1, weight=1, uniform="col")
        izq = tk.Frame(cols, bg=st.FONDO)
        izq.grid(row=0, column=0, sticky="new", padx=(0, 6))
        der = tk.Frame(cols, bg=st.FONDO)
        der.grid(row=0, column=1, sticky="new", padx=(6, 0))

        # Totales
        t1, g1, _h = uc.tarjeta(izq, "Totales", "doc")
        t1.pack(fill="x", pady=(0, 12))
        filas1 = [
            ("Total efectivo esperado", money(cierre["efectivo_esperado"])),
            ("Total efectivo contado", money(cierre["efectivo_contado"])),
            ("Total transferencias", money(cierre["transferencias"])),
            ("Cantidad de transferencias",
             str(cierre.get("n_transferencias") or 0)),
            ("Comprobantes de transferencia",
             cierre.get("comprobantes") or "—"),
            ("Total tarjetas", money(cierre["debito"] + cierre["credito"])),
            ("   · Tarjeta de débito", money(cierre["debito"])),
            ("   · Tarjeta de crédito", money(cierre["credito"])),
            ("Total BONOS", money(cierre.get("bono", 0))),
            ("Total general", money(cierre["total_general"])),
        ]
        for texto, valor in filas1:
            es_detalle = texto.startswith("   ·")
            es_clave = texto in ("Total general", "Total tarjetas")
            if texto == "Total general":
                tk.Frame(g1, bg=st.BORDE, height=1).pack(fill="x", pady=(8, 4))
            f, lbl = uc.fila(g1, texto.strip(" ·").strip() if es_detalle else texto,
                             valor, negrita=es_clave, tenue=es_detalle,
                             sangria=18 if es_detalle else 0,
                             tam=12 if texto == "Total general" else 11)
            lbl.config(wraplength=260)
            if texto == "Total general":
                lbl.config(fg=st.VERDE_OSCURO)

        # Resultado de la caja (diferencia + estado)
        t2, g2, _h = uc.tarjeta(izq, "Resultado de la caja", "history")
        t2.pack(fill="x", pady=(0, 12))
        color_dif = (st.ROJO if dif < 0 else AMBAR_TXT if dif > 0
                     else st.VERDE_OSCURO)
        uc.fila(g2, "Diferencia de caja", money(dif), negrita=True,
                color=color_dif)
        if estado == "Faltante":
            fondo, color, borde = "#FDEEEE", st.ROJO, "#F5C2C2"
        elif estado == "Sobrante":
            fondo, color, borde = "#FFF7E0", AMBAR_TXT, "#F8D98B"
        else:
            fondo, color, borde = "#ECF7F0", st.VERDE_OSCURO, "#BDE5CD"
        banda = Banda(g2, texto=estado.upper(), fondo=fondo, color=color,
                      borde=borde)
        banda.pack(fill="x", pady=(10, 0))

        # Arqueo de billetes
        t3, g3, _h = uc.tarjeta(der, "Arqueo de billetes", "banknote")
        t3.pack(fill="x", pady=(0, 12))
        enc = tk.Frame(g3, bg=uc.GRIS_F)
        enc.pack(fill="x")
        for c in range(3):
            enc.columnconfigure(c, weight=1, uniform="arq")
        for c, (txt, anc) in enumerate((("BILLETE", "w"), ("CANTIDAD", "center"),
                                        ("SUBTOTAL", "e"))):
            tk.Label(enc, text=txt, bg=uc.GRIS_F, fg=uc.MUTED,
                     font=(st.FUENTE, 9, "bold"), anchor=anc
                     ).grid(row=0, column=c, sticky="ew", padx=10, pady=8)

        billetes = cierre.get("billetes_dict") or {}
        total_contado = 0
        for denom in db.DENOMINACIONES:
            cant = int(billetes.get(str(denom), 0) or 0)
            subtotal = cant * denom
            total_contado += subtotal
            f = tk.Frame(g3, bg=st.TARJETA)
            f.pack(fill="x")
            for c in range(3):
                f.columnconfigure(c, weight=1, uniform="arq")
            tk.Label(f, text=money(denom), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 11, "bold"), anchor="w"
                     ).grid(row=0, column=0, sticky="ew", padx=10, pady=6)
            tk.Label(f, text=str(cant), bg=st.TARJETA,
                     fg=st.TEXTO if cant else uc.MUTED,
                     font=(st.FUENTE, 11), anchor="center"
                     ).grid(row=0, column=1, sticky="ew", padx=10, pady=6)
            tk.Label(f, text=money(subtotal), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 11), anchor="e"
                     ).grid(row=0, column=2, sticky="ew", padx=10, pady=6)
            tk.Frame(g3, bg=st.BORDE, height=1).pack(fill="x")

        tot = Tarjeta(g3, fondo="#ECF7F0", borde="#BDE5CD", radio=10,
                      padx=14, pady=9)
        tot.pack(fill="x", pady=(10, 0))
        tf = tk.Frame(tot.cuerpo, bg="#ECF7F0")
        tf.pack(fill="x")
        tk.Label(tf, text="TOTAL EFECTIVO CONTADO", bg="#ECF7F0", fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold")).pack(side="left")
        tk.Label(tf, text=money(total_contado), bg="#ECF7F0",
                 fg=st.VERDE_OSCURO, font=(st.FUENTE, 15, "bold")
                 ).pack(side="right")

        # ---------------- Ventas del día ----------------
        t4, g4, _h = uc.tarjeta(pagina, "Ventas del día", "cart")
        t4.pack(fill="both", expand=True)
        columnas = ("producto", "cantidad", "cliente", "medio", "comprobante",
                    "cajero", "total")
        tree = ttk.Treeview(g4, columns=columnas, show="headings", height=6)
        tree.heading("producto", text="Productos")
        tree.heading("cantidad", text="Cant.")
        tree.heading("cliente", text="Nombre / Cliente")
        tree.heading("medio", text="Formas de pago")
        tree.heading("comprobante", text="N° Comprobante")
        tree.heading("cajero", text="Registró")
        tree.heading("total", text="Total")
        tree.column("producto", width=140, anchor="w")
        tree.column("cantidad", width=52, anchor="center", stretch=False)
        tree.column("cliente", width=115, anchor="w")
        tree.column("medio", width=125, anchor="w")
        tree.column("comprobante", width=115, anchor="w")
        tree.column("cajero", width=90, anchor="w")
        tree.column("total", width=95, anchor="e")
        tree.pack(fill="both", expand=True)

        r = db.resumen(cierre["caja_id"])
        for v in r["ventas"]:
            tree.insert("", "end", values=(
                v["producto"] or "—", v["cantidad"],
                v.get("cliente") or "—",
                v.get("medios_txt") or v.get("medio") or "—",
                v.get("comprobante") or "—",
                v.get("cajero") or "—",
                money(v["total"]),
            ))
