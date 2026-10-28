# -*- coding: utf-8 -*-
"""Piezas visuales compartidas por las pantallas (tarjetas, filas, KPIs…)."""

import tkinter as tk
from tkinter import ttk

import estilos as st
import iconos as ic
from widgets_figma import Tarjeta

MUTED = st.TEXTO_SUAVE
GRIS_I, GRIS_F = "#64748B", "#F1F5F9"
AZUL_I, AZUL_F = "#2563EB", "#E8F0FE"


def dimensionar(win, ancho_max=1000, alto_max=820, ancho_min=720, alto_min=520):
    """Tamaño de una ventana secundaria adaptado a la pantalla, centrada."""
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    ancho = min(ancho_max, max(ancho_min, sw - 60))
    alto = min(alto_max, max(alto_min + 40, sh - 90))
    x = max(0, (sw - ancho) // 2)
    y = max(0, (sh - alto) // 2 - 20)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")
    win.minsize(min(ancho_min, ancho), min(alto_min, alto))


def area_scroll(parent, padx=24, pady=(20, 18)):
    """Área con scroll vertical. Devuelve (canvas, pagina)."""
    marco = tk.Frame(parent, bg=st.FONDO)
    marco.pack(side="top", fill="both", expand=True)
    canvas = tk.Canvas(marco, bg=st.FONDO, highlightthickness=0)
    barra = ttk.Scrollbar(marco, orient="vertical", command=canvas.yview)
    cont = tk.Frame(canvas, bg=st.FONDO)
    cont.bind("<Configure>",
              lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    ventana = canvas.create_window((0, 0), window=cont, anchor="nw")
    canvas.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfigure(ventana, width=e.width))
    pagina = tk.Frame(cont, bg=st.FONDO)
    pagina.pack(fill="both", expand=True, padx=padx, pady=pady)
    return canvas, pagina


def pie_fijo(parent):
    """Barra inferior fija (botones siempre visibles). Devuelve su frame."""
    pie = tk.Frame(parent, bg=st.TARJETA)
    pie.pack(side="bottom", fill="x")
    tk.Frame(pie, bg=st.BARRA_BORDE, height=1).pack(fill="x")
    fb = tk.Frame(pie, bg=st.TARJETA)
    fb.pack(fill="x", padx=24, pady=12)
    return fb


def tarjeta(parent, titulo, icono=None, padx=18, pady=14):
    """Tarjeta con encabezado. Devuelve (tarjeta, cuerpo, encabezado)."""
    t = Tarjeta(parent, radio=12, padx=padx, pady=pady)
    h = tk.Frame(t.cuerpo, bg=st.TARJETA)
    h.pack(fill="x", pady=(0, 8))
    if icono:
        tk.Label(h, image=ic.icono(icono, 20, GRIS_I),
                 bg=st.TARJETA).pack(side="left", padx=(0, 10))
    tk.Label(h, text=titulo, bg=st.TARJETA, fg=st.TEXTO,
             font=(st.FUENTE, 12, "bold")).pack(side="left")
    return t, t.cuerpo, h


def fila(parent, texto, valor="—", negrita=False, tenue=False, sangria=0,
         tam=11, color=None, bg=None):
    """Fila 'etiqueta ........ valor'. Devuelve (frame, label_valor)."""
    bg = bg or st.TARJETA
    f = tk.Frame(parent, bg=bg)
    f.pack(fill="x", pady=3)
    tk.Label(f, text=texto, bg=bg, fg=MUTED if tenue else st.TEXTO,
             font=(st.FUENTE, tam - 1 if tenue else tam,
                   "bold" if negrita else "normal"),
             anchor="w").pack(side="left", padx=(sangria, 0))
    lbl = tk.Label(f, text=valor, bg=bg, fg=color or st.TEXTO,
                   font=(st.FUENTE, tam - 1 if tenue else tam, "bold"),
                   anchor="e", justify="right")
    lbl.pack(side="right")
    return f, lbl


def kpi(parent, col, ncols, titulo, icono, color_ico=GRIS_I, fondo_ico=GRIS_F,
        borde=None, valor="—"):
    """Tarjeta de indicador dentro de un grid de `ncols` columnas iguales."""
    parent.columnconfigure(col, weight=1, uniform="kpi")
    t = Tarjeta(parent, radio=12, padx=18, pady=14, borde=borde)
    t.grid(row=0, column=col, sticky="nsew",
           padx=(0 if col == 0 else 6, 0 if col == ncols - 1 else 6))
    top = tk.Frame(t.cuerpo, bg=st.TARJETA)
    top.pack(fill="x")
    tk.Label(top, text=titulo, bg=st.TARJETA, fg=MUTED,
             font=(st.FUENTE, 10)).pack(side="left")
    tk.Label(top, image=ic.cuadro(icono, 32, color_ico, fondo_ico, 8, 17),
             bg=st.TARJETA).pack(side="right")
    lbl = tk.Label(t.cuerpo, text=valor, bg=st.TARJETA, fg=st.TEXTO,
                   font=(st.FUENTE, 24), anchor="w")
    lbl.pack(anchor="w", pady=(8, 0))
    return lbl


def entrada(parent, var=None, **kw):
    """Campo de texto con el estilo del programa (sin hacer pack)."""
    opciones = dict(font=(st.FUENTE, 11), relief="flat", bd=0, bg="#FFFFFF",
                    fg=st.TEXTO, insertbackground=st.TEXTO, highlightthickness=1,
                    highlightbackground="#D9E0EC", highlightcolor=st.ACENTO,
                    disabledbackground="#F1F5F9", disabledforeground=MUTED)
    opciones.update(kw)
    return tk.Entry(parent, textvariable=var, **opciones)
