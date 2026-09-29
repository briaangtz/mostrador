# -*- coding: utf-8 -*-
"""Historial de cierres: consulta, detalle y reapertura de cajas."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import database as db
import estilos as st
from util import money, fecha_larga, fecha_corta


class HistorialPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=st.FONDO)
        self.app = app
        self._cierres = []
        self._construir()

    def _construir(self):
        # Contenido con scroll: nada queda cortado en pantallas chicas
        contenido = st.contenido_scrollable(self)

        cab = tk.Frame(contenido, bg=st.FONDO)
        cab.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(cab, text="HISTORIAL DE CIERRES", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 22, "bold")).pack(anchor="w")
        tk.Label(cab, text="Cierres de días anteriores. Cualquier usuario puede ver "
                           "el detalle; la reapertura de una caja es una función "
                           "de DESARROLLADOR con contraseña.",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 11),
                 wraplength=780, justify="left").pack(anchor="w")

        marco = st.labelframe(contenido, " CIERRES REGISTRADOS ", padx=10, pady=10)
        marco.pack(fill="both", expand=True, padx=24, pady=(14, 0))

        columnas = ("fecha", "vendido", "efectivo", "transferencia", "tarjetas",
                    "diferencia", "estado")
        self.tree = ttk.Treeview(marco, columns=columnas, show="headings",
                                 height=14, selectmode="browse")
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

        scroll = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self._ver_detalle())

        pie = tk.Frame(contenido, bg=st.FONDO)
        pie.pack(fill="x", padx=24, pady=(12, 24))

        self._btn(pie, "Ver detalle", st.ACENTO, self._ver_detalle).pack(side="left")
        self.btn_reabrir = self._btn(pie, "Reabrir caja (contraseña)", st.ROJO,
                                     self._reabrir)
        self.btn_reabrir.pack(side="left", padx=(10, 0))

        self.lbl_resumen = tk.Label(pie, text="", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                    font=(st.FUENTE, 10))
        self.lbl_resumen.pack(side="right")

        self.lbl_vacio = tk.Label(contenido, text="Todavía no hay cierres registrados.",
                                  bg=st.FONDO, fg=st.TEXTO_SUAVE,
                                  font=(st.FUENTE, 11))

    def _btn(self, parent, texto, color, comando):
        return tk.Button(parent, text=texto, command=comando, relief="flat",
                         bg=color, fg="#ffffff", font=(st.FUENTE, 10, "bold"),
                         padx=14, pady=8, cursor="hand2")

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
        password = simpledialog.askstring(
            "Reapertura de caja",
            f"Caja del {fecha_corta(cierre['fecha'])}\n\n"
            f"Usuario: {u.get('usuario', '—')}\n"
            "Ingresá TU contraseña para autorizar la reapertura:",
            parent=self,
            show="*",
        )
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
            self.tree.insert("", "end", iid=str(i), values=(
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
                self.tree.tag_configure(str(i), foreground=st.AMBAR)
            else:
                self.tree.tag_configure(str(i), foreground=st.VERDE_OSCURO)

        if self._cierres:
            self.lbl_vacio.pack_forget()
            total = sum(c["total_vendido"] for c in self._cierres)
            self.lbl_resumen.config(
                text=f"{len(self._cierres)} cierre(s) — vendido acumulado: "
                     f"{money(total)}"
            )
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
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(740, max(560, sw - 60))
        alto = min(800, max(520, sh - 90))
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2 - 20)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(560, ancho), min(520, alto))
        self.transient(app)
        self.grab_set()

        # Contenido con scroll vertical (en pantallas chicas se baja con
        # la rueda del mouse y ningún dato queda oculto).
        marco_scroll = tk.Frame(self, bg=st.FONDO)
        marco_scroll.pack(fill="both", expand=True, padx=18, pady=16)
        self.canvas_scroll = tk.Canvas(marco_scroll, bg=st.FONDO,
                                       highlightthickness=0)
        barra = ttk.Scrollbar(marco_scroll, orient="vertical",
                              command=self.canvas_scroll.yview)
        cont = tk.Frame(self.canvas_scroll, bg=st.FONDO)
        cont.bind(
            "<Configure>",
            lambda e: self.canvas_scroll.configure(
                scrollregion=self.canvas_scroll.bbox("all")))
        ventana = self.canvas_scroll.create_window((0, 0), window=cont,
                                                   anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.canvas_scroll.pack(side="left", fill="both", expand=True)
        self.canvas_scroll.bind(
            "<Configure>",
            lambda e: self.canvas_scroll.itemconfigure(ventana, width=e.width))

        tk.Label(cont, text="DETALLE DEL CIERRE", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 18, "bold")).pack(anchor="w")
        tk.Label(cont, text=f"Fecha: {fecha_larga(cierre['fecha'])}   —   "
                            f"Hora de cierre: {cierre['hora_cierre']}",
                 bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 11)).pack(
            anchor="w", pady=(0, 4))

        apertura = db.apertura_de(cierre["caja_id"])
        tk.Label(
            cont,
            text=f"Abierta por: {apertura['usuario'] if apertura else '—'}"
                 f"   —   Cerrada por: "
                 f"{cierre.get('cerrado_por_nombre') or '(usuario eliminado)'}",
            bg=st.FONDO, fg=st.ACENTO, font=(st.FUENTE, 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Resumen general
        grupo1 = st.labelframe(cont, " TOTALES ", padx=12, pady=10)
        grupo1.pack(fill="x")
        filas1 = [
            ("Total de garrafas vendidas", str(cierre["total_garrafas"])),
            ("Total vendido", money(cierre["total_vendido"])),
            ("Operaciones realizadas", str(cierre.get("n_operaciones") or 0)),
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
            ("Total general", money(cierre["total_general"])),
            ("Diferencia de caja", money(cierre["diferencia"])),
            ("Estado", cierre["estado"]),
        ]
        for texto, valor in filas1:
            f = tk.Frame(grupo1, bg=st.FONDO)
            f.pack(fill="x", pady=1)
            es_clave = texto in ("Total general", "Diferencia de caja",
                                 "Estado", "Total tarjetas")
            es_detalle = texto.startswith("   ·")
            tk.Label(f, text=texto, bg=st.FONDO,
                     fg=st.TEXTO_SUAVE if es_detalle else st.TEXTO,
                     font=(st.FUENTE, 10 if not es_detalle else 9,
                           "bold" if es_clave else "normal"),
                     anchor="w").pack(side="left")
            color = st.TEXTO
            if texto == "Diferencia de caja":
                color = (st.ROJO if cierre["diferencia"] < 0 else
                         st.AMBAR if cierre["diferencia"] > 0 else st.VERDE_OSCURO)
            if texto == "Estado":
                color = (st.ROJO if cierre["estado"] == "Faltante" else
                         st.AMBAR if cierre["estado"] == "Sobrante" else st.VERDE_OSCURO)
            tk.Label(f, text=valor, bg=st.FONDO, fg=color,
                     font=(st.FUENTE, 10, "bold"), anchor="e").pack(side="right")

        # Arqueo
        grupo2 = st.labelframe(cont, " ARQUEO DE BILLETES ", padx=12, pady=10)
        grupo2.pack(fill="x", pady=(12, 0))

        cabeza = tk.Frame(grupo2, bg=st.BARRA, height=26)
        cabeza.pack(fill="x")
        cabeza.pack_propagate(False)
        tk.Label(cabeza, text="BILLETE", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 9, "bold"), width=14, anchor="w", padx=6).pack(
            side="left")
        tk.Label(cabeza, text="CANTIDAD", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 9, "bold"), width=10, anchor="center").pack(
            side="left")
        tk.Label(cabeza, text="SUBTOTAL", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 9, "bold"), width=14, anchor="e", padx=6).pack(
            side="right")

        billetes = cierre.get("billetes_dict") or {}
        total_contado = 0
        for denom in db.DENOMINACIONES:
            cant = int(billetes.get(str(denom), 0) or 0)
            subtotal = cant * denom
            total_contado += subtotal
            f = tk.Frame(grupo2, bg=st.TARJETA, highlightbackground=st.BORDE,
                         highlightthickness=1)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=money(denom), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 10, "bold"), width=14, anchor="w",
                     padx=6).pack(side="left", ipady=3)
            tk.Label(f, text=str(cant), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 10), width=10, anchor="center").pack(
                side="left", ipady=3)
            tk.Label(f, text=money(subtotal), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 10), width=14, anchor="e", padx=6).pack(
                side="right", ipady=3)

        f_total = tk.Frame(grupo2, bg=st.TARJETA, highlightbackground=st.BORDE,
                           highlightthickness=1)
        f_total.pack(fill="x", pady=(6, 0))
        tk.Label(f_total, text="TOTAL EFECTIVO CONTADO", bg=st.TARJETA, fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold"), anchor="w", padx=6).pack(
            side="left", ipady=5)
        tk.Label(f_total, text=money(total_contado), bg=st.TARJETA,
                 fg=st.VERDE_OSCURO, font=(st.FUENTE, 11, "bold"), anchor="e",
                 padx=6).pack(side="right", ipady=5)

        # Ventas del día
        grupo3 = st.labelframe(cont, " VENTAS DEL DÍA ", padx=10, pady=10)
        grupo3.pack(fill="both", expand=True, pady=(12, 0))

        columnas = ("producto", "cantidad", "cliente", "medio", "comprobante",
                    "cajero", "total")
        tree = ttk.Treeview(grupo3, columns=columnas, show="headings", height=6)
        tree.heading("producto", text="Productos")
        tree.heading("cantidad", text="Cant.")
        tree.heading("cliente", text="Nombre / Cliente")
        tree.heading("medio", text="Formas de pago")
        tree.heading("comprobante", text="N° Comprobante")
        tree.heading("cajero", text="Registró")
        tree.heading("total", text="Total")
        tree.column("producto", width=130, anchor="w")
        tree.column("cantidad", width=45, anchor="center")
        tree.column("cliente", width=105, anchor="w")
        tree.column("medio", width=105, anchor="w")
        tree.column("comprobante", width=110, anchor="w")
        tree.column("cajero", width=85, anchor="w")
        tree.column("total", width=90, anchor="e")
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

        tk.Button(cont, text="Cerrar", command=self.destroy, relief="flat",
                  bg="#e5eaf1", fg=st.TEXTO, font=(st.FUENTE, 10), padx=18, pady=8,
                  cursor="hand2").pack(anchor="e", pady=(12, 0))
