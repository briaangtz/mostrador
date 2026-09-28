# -*- coding: utf-8 -*-
"""Diálogo de CIERRE DE CAJA: resumen del día, arqueo de billetes y confirmación."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import database as db
import estilos as st
from util import money


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
        ancho = min(760, max(620, sw - 60))
        alto = min(820, max(560, sh - 90))
        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2 - 20)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(640, ancho), min(520, alto))
        self.transient(app)
        self.grab_set()

        self.resumen = db.resumen(caja["id"])
        self.conteo = {d: 0 for d in db.DENOMINACIONES}
        self.celdas = {}
        self.subtotales = {}

        self._construir()
        self._pintar_resumen()
        self._recalcular()

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # Contenido con scroll vertical: en pantallas chicas se baja con
        # la rueda del mouse y los botones nunca quedan fuera de la vista.
        # (App._rueda_global detecta este canvas_scroll automáticamente.)
        marco_scroll = tk.Frame(self, bg=st.FONDO)
        marco_scroll.pack(fill="both", expand=True, padx=16, pady=16)
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

        tk.Label(
            cont,
            text="CIERRE DE CAJA",
            bg=st.FONDO, fg=st.TEXTO, font=(st.FUENTE, 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            cont,
            text=f"Fecha: {db.fecha_larga(self.caja['fecha'])}",
            bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 11),
        ).pack(anchor="w", pady=(0, 2))

        u = db.usuario_sesion() or {}
        self.lbl_usuario = tk.Label(
            cont,
            text=f"Usuario que va a cerrar: {u.get('usuario', '—')} "
                 f"({u.get('rango', '—')})",
            bg=st.FONDO, fg=st.ACENTO, font=(st.FUENTE, 11, "bold"),
        )
        self.lbl_usuario.pack(anchor="w", pady=(0, 10))

        # ---------------- Resumen del día ----------------
        res = st.labelframe(cont, " RESUMEN DEL DÍA ", padx=12, pady=10)
        res.pack(fill="x")

        self.lbl_garrafas = {}
        marco_prod = tk.Frame(res, bg=st.FONDO)
        marco_prod.pack(fill="x")

        for pid, info in self.resumen["por_producto"].items():
            fila = tk.Frame(marco_prod, bg=st.FONDO)
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text=f"• {info['nombre']} vendidas", bg=st.FONDO,
                     fg=st.TEXTO, font=(st.FUENTE, 10), anchor="w").pack(
                side="left")
            lbl = tk.Label(fila, text="0", bg=st.FONDO, fg=st.TEXTO,
                           font=(st.FUENTE, 10, "bold"), anchor="e")
            lbl.pack(side="right")
            self.lbl_garrafas[pid] = lbl

        tk.Frame(res, bg=st.BORDE, height=1).pack(fill="x", pady=6)

        filas_totales = [
            ("Total de garrafas vendidas", "total_garrafas", True),
            ("Total de ventas", "total_vendido", True),
            ("Operaciones realizadas", "cantidad_ventas", False),
        ]
        self.valores_resumen = {}
        for texto, clave, negrita in filas_totales:
            f = tk.Frame(res, bg=st.FONDO)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=texto, bg=st.FONDO, fg=st.TEXTO,
                     font=(st.FUENTE, 11, "bold" if negrita else "normal"),
                     anchor="w").pack(side="left")
            lbl = tk.Label(f, text="—", bg=st.FONDO, fg=st.TEXTO,
                           font=(st.FUENTE, 11, "bold"), anchor="e")
            lbl.pack(side="right")
            self.valores_resumen[clave] = lbl

        # ---------------- Medios de pago ----------------
        med = st.labelframe(cont, " MEDIOS DE PAGO ", padx=12, pady=10)
        med.pack(fill="x", pady=(12, 0))

        filas_medio = [
            ("Efectivo esperado", "efectivo_esperado"),
            ("Transferencias", "transferencias"),
            ("Transferencias realizadas (cantidad)", "n_transferencias"),
            ("Tarjetas", "tarjetas"),
            ("   · Tarjeta de débito", "debito"),
            ("   · Tarjeta de crédito", "credito"),
            ("Total general cobrado", "total_general"),
        ]
        self.valores_medio = {}
        for i, (texto, clave) in enumerate(filas_medio):
            f = tk.Frame(med, bg=st.FONDO)
            f.pack(fill="x", pady=1)
            es_total = clave == "total_general"
            es_grupo = clave == "tarjetas"
            es_detalle = clave in ("debito", "credito")
            tk.Label(f, text=texto, bg=st.FONDO,
                     fg=st.TEXTO if not es_detalle else st.TEXTO_SUAVE,
                     font=(st.FUENTE, 11 if not es_detalle else 10,
                           "bold" if (es_total or es_grupo) else "normal"),
                     anchor="w").pack(side="left")
            lbl = tk.Label(f, text="—", bg=st.FONDO, fg=st.TEXTO,
                           font=(st.FUENTE, 11 if not es_detalle else 10,
                                 "bold"), anchor="e")
            lbl.pack(side="right")
            self.valores_medio[clave] = lbl
            if clave == "efectivo_esperado":
                self.lbl_esperado_detalle = tk.Label(
                    f, text="(incluye fondo inicial)", bg=st.FONDO, fg=st.TEXTO_SUAVE,
                    font=(st.FUENTE, 8))
                self.lbl_esperado_detalle.pack(side="right", padx=(0, 8))

        # ---------------- Detalle de transferencias ----------------
        trf = st.labelframe(cont, " COMPROBANTES DE TRANSFERENCIA ", padx=12, pady=10)
        trf.pack(fill="x", pady=(12, 0))

        columnas = ("comprobante", "hora", "producto", "cantidad", "importe")
        self.tree_transferencias = ttk.Treeview(trf, columns=columnas,
                                                show="headings", height=4)
        self.tree_transferencias.heading("comprobante", text="N° Comprobante")
        self.tree_transferencias.heading("hora", text="Hora")
        self.tree_transferencias.heading("producto", text="Producto")
        self.tree_transferencias.heading("cantidad", text="Cant.")
        self.tree_transferencias.heading("importe", text="Importe")
        self.tree_transferencias.column("comprobante", width=170, anchor="w")
        self.tree_transferencias.column("hora", width=70, anchor="center")
        self.tree_transferencias.column("producto", width=220, anchor="w")
        self.tree_transferencias.column("cantidad", width=60, anchor="center")
        self.tree_transferencias.column("importe", width=130, anchor="e")
        self.tree_transferencias.pack(fill="x")

        self.lbl_sin_transferencias = tk.Label(
            trf, text="Sin transferencias registradas en el día.",
            bg=st.FONDO, fg=st.TEXTO_SUAVE, font=(st.FUENTE, 9))

        # ---------------- Arqueo de caja ----------------
        arq = st.labelframe(cont, " ARQUEO DE CAJA — CONTEO DE BILLETES ",
                            padx=12, pady=10)
        arq.pack(fill="x", pady=(12, 0))

        enc = tk.Frame(arq, bg=st.BARRA, height=28)
        enc.pack(fill="x")
        enc.pack_propagate(False)
        for txt, w, lado in (("BILLETE", 140, "left"), ("CANTIDAD", 140, "left"),
                             ("SUBTOTAL", 180, "right")):
            tk.Label(enc, text=txt, bg=st.BARRA, fg="#ffffff",
                     font=(st.FUENTE, 9, "bold"), width=w // 10, anchor="w",
                     padx=8).pack(side=lado)

        for denom in db.DENOMINACIONES:
            fila = tk.Frame(arq, bg=st.TARJETA, highlightbackground=st.BORDE,
                            highlightthickness=1)
            fila.pack(fill="x", pady=1)

            tk.Label(fila, text=money(denom), bg=st.TARJETA, fg=st.TEXTO,
                     font=(st.FUENTE, 11, "bold"), width=13, anchor="w",
                     padx=8).pack(side="left", ipady=4)

            var = tk.StringVar(value="0")
            var.trace_add("write", lambda *_: self._recalcular())
            ent = tk.Entry(fila, textvariable=var, width=10, justify="center",
                           font=(st.FUENTE, 11), relief="solid", bd=1)
            ent.pack(side="left", padx=8, pady=4, ipady=3)
            self.celdas[denom] = var

            lbl_sub = tk.Label(fila, text="$0", bg=st.TARJETA, fg=st.TEXTO,
                               font=(st.FUENTE, 11), width=16, anchor="e", padx=8)
            lbl_sub.pack(side="right", ipady=4)
            self.subtotales[denom] = lbl_sub

        total_fila = tk.Frame(arq, bg=st.TARJETA, highlightbackground=st.BORDE,
                              highlightthickness=1)
        total_fila.pack(fill="x", pady=(8, 0))
        tk.Label(total_fila, text="TOTAL EFECTIVO CONTADO", bg=st.TARJETA,
                 fg=st.TEXTO, font=(st.FUENTE, 12, "bold"), anchor="w",
                 padx=8).pack(side="left", ipady=6)
        self.lbl_contado = tk.Label(total_fila, text="$0", bg=st.TARJETA,
                                    fg=st.VERDE_OSCURO, font=(st.FUENTE, 14, "bold"),
                                    anchor="e", padx=8)
        self.lbl_contado.pack(side="right", ipady=6)

        # ---------------- Comparación ----------------
        comp = st.labelframe(cont, " COMPARACIÓN DE CAJA ", padx=12, pady=10)
        comp.pack(fill="x", pady=(12, 0))

        c1 = tk.Frame(comp, bg=st.FONDO)
        c1.pack(fill="x")
        tk.Label(c1, text="Efectivo esperado:", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 11), anchor="w").pack(side="left")
        self.lbl_esperado2 = tk.Label(c1, text="$0", bg=st.FONDO, fg=st.TEXTO,
                                      font=(st.FUENTE, 11, "bold"))
        self.lbl_esperado2.pack(side="right")

        c2 = tk.Frame(comp, bg=st.FONDO)
        c2.pack(fill="x")
        tk.Label(c2, text="Efectivo contado:", bg=st.FONDO, fg=st.TEXTO,
                 font=(st.FUENTE, 11), anchor="w").pack(side="left")
        self.lbl_contado2 = tk.Label(c2, text="$0", bg=st.FONDO, fg=st.TEXTO,
                                     font=(st.FUENTE, 11, "bold"))
        self.lbl_contado2.pack(side="right")

        c3 = tk.Frame(comp, bg=st.FONDO)
        c3.pack(fill="x")
        tk.Label(c3, text="Diferencia (contado − esperado):", bg=st.FONDO,
                 fg=st.TEXTO, font=(st.FUENTE, 11), anchor="w").pack(side="left")
        self.lbl_diferencia = tk.Label(c3, text="$0", bg=st.FONDO, fg=st.TEXTO,
                                       font=(st.FUENTE, 11, "bold"))
        self.lbl_diferencia.pack(side="right")

        self.lbl_estado = tk.Label(comp, text="CAJA CUADRADA", bg=st.VERDE_CLARO,
                                   fg=st.VERDE_OSCURO, font=(st.FUENTE, 16, "bold"),
                                   pady=8)
        self.lbl_estado.pack(fill="x", pady=(10, 0))

        # ---------------- Botones ----------------
        botones = tk.Frame(cont, bg=st.FONDO)
        botones.pack(fill="x", pady=(14, 0))
        tk.Button(botones, text="Cancelar", command=self.destroy, relief="flat",
                  bg="#e5eaf1", fg=st.TEXTO, font=(st.FUENTE, 10), padx=16, pady=9,
                  cursor="hand2").pack(side="left")
        self.btn_cerrar = tk.Button(
            botones, text="CONFIRMAR CIERRE", command=self._confirmar,
            relief="flat", bg=st.VERDE, fg="#ffffff",
            font=(st.FUENTE, 12, "bold"), padx=24, pady=10, cursor="hand2",
        )
        self.btn_cerrar.pack(side="right")
        self.btn_cerrar.bind("<Enter>", lambda e: self.btn_cerrar.config(bg=st.VERDE_OSCURO))
        self.btn_cerrar.bind("<Leave>", lambda e: self.btn_cerrar.config(bg=st.VERDE))

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
            text=f"(ventas {money(r['efectivo'])} + fondo {money(fondo)})"
        )

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

        esperado = self.resumen["efectivo_esperado"]
        diferencia = total - esperado
        estado, etiqueta = db.clasificar_diferencia(diferencia)

        self.lbl_contado.config(text=money(total))
        self.lbl_contado2.config(text=money(total))
        self.lbl_esperado2.config(text=money(esperado))
        self.lbl_diferencia.config(
            text=money(diferencia),
            fg=st.ROJO if diferencia < 0 else (st.AMBAR if diferencia > 0 else st.VERDE_OSCURO),
        )
        self.lbl_estado.config(text=etiqueta)
        if estado == "Faltante":
            self.lbl_estado.config(bg=st.ROJO_CLARO, fg=st.ROJO)
        elif estado == "Sobrante":
            self.lbl_estado.config(bg=st.AMBAR_CLARO, fg=st.AMBAR)
        else:
            self.lbl_estado.config(bg=st.VERDE_CLARO, fg=st.VERDE_OSCURO)

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
        password = simpledialog.askstring(
            "Autenticación de cierre",
            f"Usuario: {u['usuario'] if u else '—'}\n\n"
            "Para cerrar la caja ingresá TU contraseña:",
            parent=self,
            show="*",
        )
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
            f"Responsable: {u['usuario'] if u else '—'}\n"
            f"Garrafas vendidas: {self.resumen['total_garrafas']}\n"
            f"Total vendido: {money(self.resumen['total_vendido'])}\n"
            f"Operaciones: {self.resumen['cantidad_ventas']}\n"
            f"Transferencias: {money(self.resumen['transferencias'])} "
            f"({self.resumen['n_transferencias']} comprobantes)\n"
            f"Tarjetas: {money(self.resumen['debito'] + self.resumen['credito'])} "
            f"(Débito {money(self.resumen['debito'])} / "
            f"Crédito {money(self.resumen['credito'])})\n"
            f"Efectivo esperado: {money(self._esperado_actual)}\n"
            f"Efectivo contado: {money(self._contado_actual)}\n"
            f"Diferencia: {money(self._diferencia_actual)}\n"
            f"Estado: {self._estado_actual}\n\n"
            "¿Confirmar el cierre definitivo de la caja?\n"
            "Una vez confirmado, la caja quedará bloqueada."
        )
        if not messagebox.askyesno("CONFIRMAR CIERRE", resumen_txt, parent=self):
            return

        db.guardar_cierre(
            self.caja["id"],
            total_garrafas=self.resumen["total_garrafas"],
            total_vendido=self.resumen["total_vendido"],
            efectivo_esperado=self._esperado_actual,
            efectivo_contado=self._contado_actual,
            transferencias=self.resumen["transferencias"],
            debito=self.resumen["debito"],
            credito=self.resumen["credito"],
            total_general=self.resumen["total_general"],
            diferencia=self._diferencia_actual,
            estado=self._estado_actual,
            billetes={str(d): c for d, c in self.conteo.items()},
            n_transferencias=self.resumen["n_transferencias"],
        )

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
            except Exception:
                pass
