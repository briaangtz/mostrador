# -*- coding: utf-8 -*-
"""Diálogo de CIERRE DE CAJA: resumen del día, arqueo de billetes y confirmación."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import database as db
import errores
import estilos as st
import iconos as ic
from util import money
from widgets_figma import Tarjeta, Btn, Banda


def pedir_password(parent, usuario):
    """Pide la contraseña del responsable (ventana propia, con el estilo del
    programa). Devuelve el texto escrito o None si se cancela."""
    dlg = tk.Toplevel(parent)
    dlg.title("Autenticación de cierre")
    dlg.configure(bg=st.FONDO)
    dlg.resizable(False, False)
    dlg.transient(parent)
    resultado = {"valor": None}

    cont = tk.Frame(dlg, bg=st.FONDO)
    cont.pack(fill="both", expand=True, padx=24, pady=22)
    cab = tk.Frame(cont, bg=st.FONDO)
    cab.pack(fill="x")
    tk.Label(cab, image=ic.cuadro("lock", 46, "#2563EB", "#E8F0FE", 12, 24, 1.8),
             bg=st.FONDO).pack(side="left", padx=(0, 14))
    col = tk.Frame(cab, bg=st.FONDO)
    col.pack(side="left")
    tk.Label(col, text="Autenticación de cierre", bg=st.FONDO, fg=st.TEXTO,
             font=(st.FUENTE, 14, "bold")).pack(anchor="w")
    tk.Label(col, text=f"Usuario: {usuario}", bg=st.FONDO, fg=st.TEXTO_SUAVE,
             font=(st.FUENTE, 10)).pack(anchor="w")

    tk.Label(cont, text="Para cerrar la caja ingresá TU contraseña:",
             bg=st.FONDO, fg=st.TEXTO, font=(st.FUENTE, 10)
             ).pack(anchor="w", pady=(16, 6))
    var = tk.StringVar()
    ent = tk.Entry(cont, textvariable=var, show="•", width=34,
                   font=(st.FUENTE, 12), relief="flat", bd=0, bg="#FFFFFF",
                   fg=st.TEXTO, insertbackground=st.TEXTO,
                   highlightthickness=1, highlightbackground="#D9E0EC",
                   highlightcolor=st.ACENTO)
    ent.pack(fill="x", ipady=8)

    def aceptar(_e=None):
        resultado["valor"] = var.get()
        dlg.destroy()

    def cancelar(_e=None):
        dlg.destroy()

    fila = tk.Frame(cont, bg=st.FONDO)
    fila.pack(fill="x", pady=(18, 0))
    Btn(fila, text="Cancelar", command=cancelar, bg="#E5EAF1", fg=st.TEXTO,
        font=(st.FUENTE, 10), padx=18, pady=9).pack(side="left")
    Btn(fila, text="CONFIRMAR", command=aceptar, bg=st.VERDE, fg="#ffffff",
        font=(st.FUENTE, 10, "bold"), padx=22, pady=9).pack(side="right")
    dlg.bind("<Return>", aceptar)
    dlg.bind("<Escape>", cancelar)
    dlg.protocol("WM_DELETE_WINDOW", cancelar)

    # Centrada sobre la ventana que la llamó
    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
    try:
        dlg.grab_set()
    except tk.TclError:
        pass
    ent.focus_set()
    parent.wait_window(dlg)
    return resultado["valor"]


class CierreDialog(tk.Toplevel):
    def __init__(self, app, caja, on_cerrado=None):
        super().__init__(app)
        self.app = app
        self.caja = caja
        self.on_cerrado = on_cerrado

        self.title("Cierre de caja")
        self.configure(bg=st.FONDO)

        # Se adapta al tamaño de la pantalla (nada cortado ni fuera de vista)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(1000, max(720, sw - 60))
        alto = min(820, max(560, sh - 90))
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2 - 20)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(720, ancho), min(520, alto))
        self.transient(app)
        self.grab_set()

        self.resumen = db.resumen(caja["id"])
        # Efectivo esperado antes de descontar gastos (ventas en efectivo + fondo)
        self._efectivo_base = self.resumen["efectivo_base"]
        self.gastos = 0.0
        self.conteo = {d: 0 for d in db.DENOMINACIONES}
        self.celdas = {}
        self.subtotales = {}

        self._construir()
        self._pintar_resumen()
        self._recalcular()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        MUTED = st.TEXTO_SUAVE
        GRIS_I, GRIS_F = "#64748B", "#F1F5F9"
        AZUL_I, AZUL_F = "#2563EB", "#E8F0FE"

        # ---------- Pie fijo: los botones nunca quedan fuera de la vista ----------
        pie = tk.Frame(self, bg=st.TARJETA)
        pie.pack(side="bottom", fill="x")
        tk.Frame(pie, bg=st.BARRA_BORDE, height=1).pack(fill="x")
        fb = tk.Frame(pie, bg=st.TARJETA)
        fb.pack(fill="x", padx=24, pady=12)
        Btn(fb, text="Cancelar", command=self.destroy, bg="#E5EAF1",
            fg=st.TEXTO, font=(st.FUENTE, 10), padx=20, pady=10
            ).pack(side="left")
        self.btn_cerrar = Btn(
            fb, text="CONFIRMAR CIERRE", command=self._confirmar, bg=st.VERDE,
            fg="#ffffff", font=(st.FUENTE, 12, "bold"), padx=28, pady=11)
        self.btn_cerrar.pack(side="right")

        # ---------- Contenido con scroll vertical ----------
        # (App._rueda_global detecta este canvas_scroll automáticamente.)
        marco_scroll = tk.Frame(self, bg=st.FONDO)
        marco_scroll.pack(side="top", fill="both", expand=True)
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

        pagina = tk.Frame(cont, bg=st.FONDO)
        pagina.pack(fill="both", expand=True, padx=24, pady=(20, 18))

        # ---------- Utilidades de armado ----------
        def tarjeta(parent, titulo, icono):
            t = Tarjeta(parent, radio=12, padx=18, pady=14)
            t.pack(fill="x", pady=(0, 12))
            h = tk.Frame(t.cuerpo, bg=st.TARJETA)
            h.pack(fill="x", pady=(0, 8))
            tk.Label(h, image=ic.icono(icono, 20, GRIS_I),
                     bg=st.TARJETA).pack(side="left", padx=(0, 10))
            tk.Label(h, text=titulo, bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 12, "bold")).pack(side="left")
            return t.cuerpo

        def fila(parent, texto, valor="—", negrita=False, tenue=False,
                 sangria=0, tam=11):
            f = tk.Frame(parent, bg=st.TARJETA)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=texto, bg=st.TARJETA,
                     fg=MUTED if tenue else st.TEXTO,
                     font=(st.FUENTE, tam - 1 if tenue else tam,
                           "bold" if negrita else "normal"),
                     anchor="w").pack(side="left", padx=(sangria, 0))
            lbl = tk.Label(f, text=valor, bg=st.TARJETA, fg=st.TEXTO,
                           font=(st.FUENTE, tam - 1 if tenue else tam, "bold"),
                           anchor="e")
            lbl.pack(side="right")
            return f, lbl

        # ---------- Título ----------
        tk.Label(pagina, text="Cierre de caja", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 24, "bold")).pack(anchor="w")
        tk.Label(pagina, text=f"Fecha: {db.fecha_larga(self.caja['fecha'])}",
                 bg=st.FONDO, fg=MUTED, font=(st.FUENTE, 11)
                 ).pack(anchor="w", pady=(2, 8))

        u = db.usuario_sesion() or {}
        chip = Tarjeta(pagina, fondo=AZUL_F, borde="#C3D6F8", radio=14,
                       padx=14, pady=7, ancho_auto=True)
        chip.pack(anchor="w")
        cf = tk.Frame(chip.cuerpo, bg=AZUL_F)
        cf.pack()
        tk.Label(cf, image=ic.icono("user", 18, AZUL_I, 1.8),
                 bg=AZUL_F).pack(side="left", padx=(0, 8))
        self.lbl_usuario = tk.Label(
            cf, text=f"Usuario que va a cerrar: {u.get('usuario', '—')} "
                     f"({u.get('rango', '—')})",
            bg=AZUL_F, fg=st.ACENTO_OSCURO, font=(st.FUENTE, 10, "bold"))
        self.lbl_usuario.pack(side="left")

        # ---------- Totales del día ----------
        kpis = tk.Frame(pagina, bg=st.FONDO)
        kpis.pack(fill="x", pady=(14, 12))
        for i in range(3):
            kpis.columnconfigure(i, weight=1, uniform="kpi")
        self.valores_resumen = {}
        for i, (titulo, clave, icono, ci, cf_) in enumerate((
                ("Garrafas vendidas", "total_garrafas", "cube", GRIS_I, GRIS_F),
                ("Total de ventas", "total_vendido", "dollar", AZUL_I, AZUL_F),
                ("Operaciones realizadas", "cantidad_ventas", "clipboard",
                 GRIS_I, GRIS_F))):
            t = Tarjeta(kpis, radio=12, padx=18, pady=14,
                        borde="#C3D6F8" if i == 1 else None)
            t.grid(row=0, column=i, sticky="nsew",
                   padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            top = tk.Frame(t.cuerpo, bg=st.TARJETA)
            top.pack(fill="x")
            tk.Label(top, text=titulo, bg=st.TARJETA, fg=MUTED,
                     font=(st.FUENTE, 10)).pack(side="left")
            tk.Label(top, image=ic.cuadro(icono, 32, ci, cf_, 8, 17),
                     bg=st.TARJETA).pack(side="right")
            lbl = tk.Label(t.cuerpo, text="—", bg=st.TARJETA, fg=st.TEXTO,
                           font=(st.FUENTE, 24), anchor="w")
            lbl.pack(anchor="w", pady=(8, 0))
            self.valores_resumen[clave] = lbl

        # ---------- Dos columnas ----------
        cols = tk.Frame(pagina, bg=st.FONDO)
        cols.pack(fill="both", expand=True)
        cols.columnconfigure(0, weight=1, uniform="col")
        cols.columnconfigure(1, weight=1, uniform="col")
        izq = tk.Frame(cols, bg=st.FONDO)
        izq.grid(row=0, column=0, sticky="new", padx=(0, 6))
        der = tk.Frame(cols, bg=st.FONDO)
        der.grid(row=0, column=1, sticky="new", padx=(6, 0))

        # ---------------- Resumen por producto ----------------
        self.lbl_garrafas = {}
        res = tarjeta(izq, "Resumen del día", "cube")
        for pid, info in self.resumen["por_producto"].items():
            _f, lbl = fila(res, f"{info['nombre']} vendidas")
            self.lbl_garrafas[pid] = lbl
            lbl.config(text="0")
        if not self.resumen["por_producto"]:
            tk.Label(res, text="Sin productos vendidos.", bg=st.TARJETA,
                     fg=MUTED, font=(st.FUENTE, 10)).pack(anchor="w")

        # ---------------- Medios de pago ----------------
        med = tarjeta(izq, "Medios de pago", "card")
        filas_medio = [
            ("Efectivo esperado", "efectivo_esperado"),
            ("Transferencias", "transferencias"),
            ("Transferencias realizadas (cantidad)", "n_transferencias"),
            ("Tarjetas", "tarjetas"),
            ("Tarjeta de débito", "debito"),
            ("Tarjeta de crédito", "credito"),
            ("BONOS", "bono"),
            ("Total general cobrado", "total_general"),
        ]
        self.valores_medio = {}
        for texto, clave in filas_medio:
            es_total = clave == "total_general"
            es_grupo = clave == "tarjetas"
            es_detalle = clave in ("debito", "credito")
            if es_total:
                tk.Frame(med, bg=st.BORDE, height=1).pack(fill="x", pady=(8, 4))
            f, lbl = fila(med, texto, negrita=es_total or es_grupo,
                          tenue=es_detalle, sangria=18 if es_detalle else 0,
                          tam=12 if es_total else 11)
            if es_total:
                lbl.config(fg=st.VERDE_OSCURO)
            self.valores_medio[clave] = lbl
            if clave == "efectivo_esperado":
                self.lbl_esperado_detalle = tk.Label(
                    f, text="(incluye fondo inicial)", bg=st.TARJETA,
                    fg=MUTED, font=(st.FUENTE, 8))
                self.lbl_esperado_detalle.pack(side="right", padx=(0, 8))

        # ---------------- Detalle de transferencias ----------------
        trf = tarjeta(izq, "Comprobantes de transferencia", "transfer")
        columnas = ("comprobante", "hora", "producto", "cantidad", "importe")
        self.tree_transferencias = ttk.Treeview(trf, columns=columnas,
                                                show="headings", height=4)
        self.tree_transferencias.heading("comprobante", text="N° Comprobante")
        self.tree_transferencias.heading("hora", text="Hora")
        self.tree_transferencias.heading("producto", text="Productos")
        self.tree_transferencias.heading("cantidad", text="Cant.")
        self.tree_transferencias.heading("importe", text="Importe")
        self.tree_transferencias.column("comprobante", width=125, anchor="w")
        self.tree_transferencias.column("hora", width=52, anchor="center", stretch=False)
        self.tree_transferencias.column("producto", width=120, anchor="w")
        self.tree_transferencias.column("cantidad", width=48, anchor="center", stretch=False)
        self.tree_transferencias.column("importe", width=90, anchor="e")
        self.tree_transferencias.pack(fill="x")

        self.lbl_sin_transferencias = tk.Label(
            trf, text="Sin transferencias registradas en el día.",
            bg=st.TARJETA, fg=MUTED, font=(st.FUENTE, 9))

        # ---------------- Arqueo de caja ----------------
        arq = tarjeta(der, "Arqueo de caja — conteo de billetes", "banknote")
        enc = tk.Frame(arq, bg=GRIS_F)
        enc.pack(fill="x")
        for c in range(3):
            enc.columnconfigure(c, weight=1, uniform="arq")
        for c, (txt, anc) in enumerate((("BILLETE", "w"), ("CANTIDAD", "center"),
                                        ("SUBTOTAL", "e"))):
            tk.Label(enc, text=txt, bg=GRIS_F, fg=MUTED,
                     font=(st.FUENTE, 9, "bold"), anchor=anc if anc != "center"
                     else "center").grid(row=0, column=c, sticky="ew",
                                         padx=10, pady=8)

        for denom in db.DENOMINACIONES:
            f = tk.Frame(arq, bg=st.TARJETA)
            f.pack(fill="x")
            for c in range(3):
                f.columnconfigure(c, weight=1, uniform="arq")
            tk.Label(f, text=money(denom), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 11, "bold"), anchor="w"
                     ).grid(row=0, column=0, sticky="ew", padx=10, pady=5)

            var = tk.StringVar(value="0")
            var.trace_add("write", lambda *_: self._recalcular())
            ent = tk.Entry(f, textvariable=var, width=8, justify="center",
                           font=(st.FUENTE, 11), relief="flat", bd=0,
                           bg="#FFFFFF", fg=st.TEXTO, insertbackground=st.TEXTO,
                           highlightthickness=1, highlightbackground="#D9E0EC",
                           highlightcolor=st.ACENTO)
            ent.grid(row=0, column=1, padx=10, pady=5, ipady=4)
            self.celdas[denom] = var

            lbl_sub = tk.Label(f, text="$0", bg=st.TARJETA, fg=st.TEXTO,
                               font=(st.FUENTE, 11), anchor="e")
            lbl_sub.grid(row=0, column=2, sticky="ew", padx=10, pady=5)
            self.subtotales[denom] = lbl_sub
            tk.Frame(arq, bg=st.BORDE, height=1).pack(fill="x")

        tot = Tarjeta(arq, fondo="#ECF7F0", borde="#BDE5CD", radio=10,
                      padx=14, pady=9)
        tot.pack(fill="x", pady=(10, 0))
        tf = tk.Frame(tot.cuerpo, bg="#ECF7F0")
        tf.pack(fill="x")
        tk.Label(tf, text="TOTAL EFECTIVO CONTADO", bg="#ECF7F0", fg=st.TEXTO,
                 font=(st.FUENTE, 11, "bold")).pack(side="left")
        self.lbl_contado = tk.Label(tf, text="$0", bg="#ECF7F0",
                                    fg=st.VERDE_OSCURO,
                                    font=(st.FUENTE, 15, "bold"))
        self.lbl_contado.pack(side="right")

        # ---------------- Comparación ----------------
        comp = tarjeta(der, "Comparación de caja", "history")
        _f, self.lbl_esperado2 = fila(comp, "Efectivo esperado:")
        _f, self.lbl_contado2 = fila(comp, "Efectivo contado:")
        _f, self.lbl_diferencia = fila(comp, "Diferencia (contado − esperado):",
                                       negrita=True)
        self.lbl_esperado2.config(text="$0")
        self.lbl_contado2.config(text="$0")
        self.lbl_diferencia.config(text="$0")
        # -------- Gastos del día (se descuentan del efectivo esperado) --------
        _f, self.lbl_gastos = fila(comp, "Gastos del día:")
        self.ent_gastos = tk.Entry(_f, font=(st.FUENTE, 11), justify="right",
                                   width=12, relief="solid", borderwidth=1)
        self.ent_gastos.insert(0, "0")
        self.ent_gastos.pack(side="right")
        self.ent_gastos.bind("<KeyRelease>", lambda e: self._on_gastos_cambio())
        self.lbl_estado = Banda(comp, texto="CAJA CUADRADA")
        self.lbl_estado.pack(fill="x", pady=(12, 0))

    # ------------------------------------------------------------- Lógica
    def _pintar_resumen(self):
        r = self.resumen
        for pid, lbl in self.lbl_garrafas.items():
            info = r["por_producto"].get(pid)
            lbl.config(text=str(info["cantidad"]) if info else "0")

        self.valores_resumen["total_garrafas"].config(text=str(r["total_garrafas"]))
        self.valores_resumen["total_vendido"].config(text=money(r["total_vendido"]))
        self.valores_resumen["cantidad_ventas"].config(
            text=str(r["cantidad_ventas"]))

        self.valores_medio["efectivo_esperado"].config(text=money(r["efectivo_esperado"]))
        self.valores_medio["transferencias"].config(text=money(r["transferencias"]))
        self.valores_medio["n_transferencias"].config(text=str(r["n_transferencias"]))
        self.valores_medio["tarjetas"].config(
            text=money(r["debito"] + r["credito"]))
        self.valores_medio["debito"].config(text=money(r["debito"]))
        self.valores_medio["credito"].config(text=money(r["credito"]))
        self.valores_medio["bono"].config(text=money(r.get("bono", 0)))
        self.valores_medio["total_general"].config(text=money(r["total_general"]))

        # Detalle de comprobantes de transferencia
        self.tree_transferencias.delete(
            *self.tree_transferencias.get_children())
        for t in r["transferencias_detalle"]:
            hora = t["fecha_hora"].split(" ")[1][:5] if t["fecha_hora"] else ""
            self.tree_transferencias.insert("", "end", values=(
                t["comprobante"] or "—",
                hora,
                t["producto"] or "—",
                t["cantidad"],
                money(t["total"]),
            ))
        if r["n_transferencias"]:
            self.lbl_sin_transferencias.pack_forget()
        else:
            self.lbl_sin_transferencias.pack(anchor="w", pady=(4, 0))

        fondo = db.get_fondo_inicial()
        self.lbl_esperado_detalle.config(
            text=f"(ventas {money(r['efectivo'])} + fondo {money(fondo)}"
                 f"{' − gastos ' + money(r['gastos']) if r['gastos'] else ''})"
        )

    def _on_gastos_cambio(self):
        """Recalcula esperado y diferencia cuando el usuario edita los gastos."""
        try:
            txt = self.ent_gastos.get().strip().replace(".", "").replace(",", ".")
            self.gastos = float(txt) if txt else 0.0
        except ValueError:
            self.gastos = 0.0
        self._recalcular()

    def _recalcular(self):
        total = 0
        for denom in db.DENOMINACIONES:
            cant = self.conteo[denom]
            valor = self.celdas[denom].get().strip()
            if valor == "":
                cant = 0
            else:
                try:
                    cant = int(float(valor.replace(".", "").replace(",", ".")))
                except ValueError:
                    cant = 0
                if cant < 0:
                    cant = 0
            self.conteo[denom] = cant
            subtotal = denom * cant
            total += subtotal
            self.subtotales[denom].config(text=money(subtotal))

        # El esperado descuenta los gastos del día
        esperado = self._efectivo_base - self.gastos
        diferencia = total - esperado
        estado, etiqueta = db.clasificar_diferencia(diferencia)

        self.lbl_contado.config(text=money(total))
        self.lbl_contado2.config(text=money(total))
        self.lbl_esperado2.config(text=money(esperado))
        self.lbl_diferencia.config(
            text=money(diferencia),
            fg=st.ROJO if diferencia < 0 else ("#B45309" if diferencia > 0 else st.VERDE_OSCURO),
        )
        if estado == "Faltante":
            self.lbl_estado.set(etiqueta, "#FDEEEE", st.ROJO, "#F5C2C2")
        elif estado == "Sobrante":
            self.lbl_estado.set(etiqueta, "#FFF7E0", "#B45309", "#F8D98B")
        else:
            self.lbl_estado.set(etiqueta, "#ECF7F0", st.VERDE_OSCURO, "#BDE5CD")

        self._estado_actual = estado
        self._contado_actual = total
        self._esperado_actual = esperado
        self._diferencia_actual = diferencia

    def _confirmar(self):
        # Validación interna de permisos (además de no mostrar el botón)
        if not db.puede("cerrar_caja"):
            messagebox.showerror("Sin permisos",
                                 "Tu usuario no tiene permiso para cerrar cajas.",
                                 parent=self)
            return
        if not db.caja_esta_abierta(self.caja["id"]):
            messagebox.showerror("Caja cerrada",
                                 "Esta caja ya fue cerrada y está bloqueada.",
                                 parent=self)
            return

        if self._contado_actual == 0 and self.resumen["efectivo"] > 0:
            if not messagebox.askyesno(
                "Confirmar",
                "No has ingresado el conteo de billetes y hay ventas en efectivo.\n"
                "¿Deseas continuar igualmente?",
                parent=self,
            ):
                return

        # -------- Autenticación: usuario + contraseña del responsable --------
        u = db.usuario_sesion()
        if not u:
            messagebox.showerror(
                "Sin sesión",
                "No hay usuario conectado. Iniciá sesión e intentá de nuevo.",
                parent=self)
            return
        password = pedir_password(self, u["usuario"])
        try:
            self.grab_set()
        except tk.TclError:
            pass
        if password is None:
            return
        if not db.validar_password_sesion(password):
            messagebox.showerror(
                "Contraseña incorrecta",
                "La contraseña no corresponde al usuario conectado.\n"
                "El cierre NO se realizó.", parent=self)
            return

        resumen_txt = (
            f"Fecha: {db.fecha_larga(self.caja['fecha'])}\n"
            f"Responsable: {u['usuario']}\n"
            f"Garrafas vendidas: {self.resumen['total_garrafas']}\n"
            f"Total vendido: {money(self.resumen['total_vendido'])}\n"
            f"Operaciones: {self.resumen['cantidad_ventas']}\n"
            f"Transferencias: {money(self.resumen['transferencias'])} "
            f"({self.resumen['n_transferencias']} comprobantes)\n"
            f"Tarjetas: {money(self.resumen['debito'] + self.resumen['credito'])} "
            f"(Débito {money(self.resumen['debito'])} / "
            f"Crédito {money(self.resumen['credito'])})\n"
            f"BONOS: {money(self.resumen.get('bono', 0))}\n"
            f"Efectivo esperado: {money(self._esperado_actual)}\n"
            f"Efectivo contado: {money(self._contado_actual)}\n"
            f"Diferencia: {money(self._diferencia_actual)}\n"
            f"Estado: {self._estado_actual}\n\n"
            "¿Confirmar el cierre definitivo de la caja?\n"
            "Una vez confirmado, la caja quedará bloqueada."
        )
        if not messagebox.askyesno("CONFIRMAR CIERRE", resumen_txt, parent=self):
            return

        try:
            db.guardar_cierre(
                self.caja["id"],
                total_garrafas=self.resumen["total_garrafas"],
                total_vendido=self.resumen["total_vendido"],
                efectivo_esperado=self._esperado_actual,
                efectivo_contado=self._contado_actual,
                transferencias=self.resumen["transferencias"],
                debito=self.resumen["debito"],
                credito=self.resumen["credito"],
                bono=self.resumen.get("bono", 0),
                total_general=self.resumen["total_general"],
                diferencia=self._diferencia_actual,
                estado=self._estado_actual,
                billetes={str(d): c for d, c in self.conteo.items()},
                n_transferencias=self.resumen["n_transferencias"],
                gastos=self.gastos,
            )
        except Exception as e:
            errores.mostrar(
                "Error al cerrar", e, parent=self,
                contexto="guardar el cierre de caja",
                mensaje="No se pudo guardar el cierre.\n"
                        "La caja NO se cerró: los datos cargados siguen "
                        "ahí. Probá de nuevo.")
            return

        # Respaldo automático en el momento crítico: cierre de caja
        try:
            db.respaldar("cierre de caja")
        except Exception:
            pass

        # El diálogo se cierra acá (siempre), sin ventanas de más:
        # el detalle del cierre queda registrado y visible en Inicio.
        self.destroy()
        if self.on_cerrado:
            try:
                self.on_cerrado()
            except Exception as e:
                errores.mostrar(
                    "Error al actualizar", e, parent=self,
                    contexto="refrescar la pantalla tras el cierre",
                    mensaje="El cierre se guardó bien, pero la pantalla no "
                            "se actualizó.\nAbrí Inicio de nuevo para ver "
                            "los datos.")
