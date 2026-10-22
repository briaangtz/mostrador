# -*- coding: utf-8 -*-
"""Estilos y widgets reutilizables de la interfaz.

Paleta inspirada en el diseño moderno: sidebar oscuro, fondo claro,
tarjetas blancas con sombra sutil y colores de marca por medio de pago.
"""

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Paleta de colores (acercada al diseño de referencia)
# ---------------------------------------------------------------------------
FONDO = "#f1f5f9"          # fondo claro general
TARJETA = "#ffffff"        # tarjetas blancas
BORDE = "#e2e8f0"          # borde sutil de tarjetas
BARRA = "#0f172a"          # sidebar / cabecera de login (azul muy oscuro)
BARRA_TEXTO = "#ffffff"
ACENTO = "#2563eb"         # azul principal (botones, íconos activos)
ACENTO_OSCURO = "#1d4ed8"
TEXTO = "#0f172a"          # texto principal casi negro
TEXTO_SUAVE = "#64748b"    # texto secundario gris azulado
VERDE = "#16a34a"          # verde éxito / caja abierta
VERDE_OSCURO = "#15803d"
ROJO = "#dc2626"           # rojo peligro / cerrado
AMBAR = "#d97706"
ROJO_CLARO = "#fee2e2"
VERDE_CLARO = "#dcfce7"
AMBAR_CLARO = "#fef3c7"

# Colores de íconos por medio de pago
COLOR_GARRAFA = "#2563eb"   # azul
COLOR_TOTAL   = "#059669"   # verde esmeralda
COLOR_EFECTIVO= "#7c3aed"   # púrpura
COLOR_TRANS   = "#0284c7"   # cielo
COLOR_TARJETA = "#ea580c"   # naranja
COLOR_BONO    = "#be185d"   # rosa
COLOR_VENTAS  = "#8b5cf6"   # violeta

FUENTE = "Segoe UI"


def aplicar_estilo(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=(FUENTE, 10), background=FONDO, foreground=TEXTO)
    style.configure("TFrame", background=FONDO)
    style.configure("Card.TFrame", background=TARJETA)
    style.configure("TLabel", background=FONDO, foreground=TEXTO)
    style.configure("Card.TLabel", background=TARJETA, foreground=TEXTO)
    style.configure("Titulo.TLabel", background=FONDO, foreground=TEXTO,
                    font=(FUENTE, 22, "bold"))
    style.configure("Subtitulo.TLabel", background=FONDO, foreground=TEXTO_SUAVE,
                    font=(FUENTE, 11))
    style.configure("Encabezado.TLabelframe", background=FONDO, foreground=TEXTO,
                    font=(FUENTE, 11, "bold"))
    style.configure("Encabezado.TLabelframe.Label", background=FONDO,
                    foreground=TEXTO, font=(FUENTE, 11, "bold"))
    style.configure("CardEncabezado.TLabel", background=TARJETA,
                    foreground=TEXTO_SUAVE, font=(FUENTE, 9, "bold"))
    style.configure("CardValor.TLabel", background=TARJETA, foreground=TEXTO,
                    font=(FUENTE, 18, "bold"))
    style.configure("CardValorChico.TLabel", background=TARJETA,
                    foreground=TEXTO, font=(FUENTE, 14, "bold"))
    style.configure("TButton", font=(FUENTE, 10), padding=(10, 6))

    style.configure("Acento.TButton", background=ACENTO, foreground="#ffffff",
                    font=(FUENTE, 11, "bold"), padding=(16, 10))
    style.map("Acento.TButton",
              background=[("active", ACENTO_OSCURO), ("disabled", "#9db7ee")],
              foreground=[("disabled", "#eaf1ff")])

    style.configure("Exito.TButton", background=VERDE, foreground="#ffffff",
                    font=(FUENTE, 11, "bold"), padding=(16, 10))
    style.map("Exito.TButton",
              background=[("active", VERDE_OSCURO), ("disabled", "#a3d9b5")],
              foreground=[("disabled", "#eafaf0")])

    style.configure("Peligro.TButton", background=ROJO, foreground="#ffffff",
                    font=(FUENTE, 10, "bold"), padding=(12, 8))
    style.map("Peligro.TButton",
              background=[("active", "#b91c1c"), ("disabled", "#f0a8a8")],
              foreground=[("disabled", "#fdecec")])

    style.configure("Secundario.TButton", background="#e5eaf1", foreground=TEXTO,
                    font=(FUENTE, 10), padding=(12, 8))
    style.map("Secundario.TButton", background=[("active", "#d5dce6")])

    style.configure("Treeview", font=(FUENTE, 10), rowheight=28,
                    background="#ffffff", fieldbackground="#ffffff", foreground=TEXTO,
                    bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE)
    style.configure("Treeview.Heading", font=(FUENTE, 10, "bold"),
                    background="#f1f5f9", foreground=TEXTO,
                    bordercolor=BORDE)
    style.map("Treeview", background=[("selected", ACENTO)],
              foreground=[("selected", "#ffffff")])

    style.configure("TCombobox", padding=(6, 4))
    style.configure("TSpinbox", padding=(6, 4))
    style.configure("Labelframe", background=FONDO)
    return style


def tarjeta(parent, titulo, valor_inicial="—", color=ACENTO, detalle="",
            ancho_chico=False, fuente_valor=18):
    """Crea una tarjeta de resumen moderna con ícono de color.

    Devuelve (frame, etiqueta_valor). El detalle queda en frame.lbl_detalle.
    """
    frame = tk.Frame(parent, bg=TARJETA, bd=0,
                     highlightbackground=BORDE, highlightthickness=1)
    # Ícono circular de color
    icono = tk.Label(frame, text="●", bg=TARJETA, fg=color,
                     font=(FUENTE, 14 if ancho_chico else 16, "bold"))
    icono.pack(fill="x", padx=14, pady=(10, 0))
    lbl_t = tk.Label(frame, text=titulo.upper(), bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 9, "bold"), anchor="w")
    lbl_t.pack(fill="x", padx=14, pady=(4, 0))
    lbl_v = tk.Label(frame, text=valor_inicial, bg=TARJETA, fg=TEXTO,
                     font=(FUENTE, fuente_valor if not ancho_chico else 15,
                           "bold"), anchor="w")
    lbl_v.pack(fill="x", padx=14, pady=(2, 0))
    lbl_d = tk.Label(frame, text=detalle, bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 8), anchor="w")
    lbl_d.pack(fill="x", padx=14, pady=(0, 10))
    frame.lbl_detalle = lbl_d
    frame.lbl_titulo = lbl_t
    frame.lbl_valor = lbl_v
    return frame, lbl_v


def etiqueta(parent, texto, **kwargs):
    return tk.Label(parent, text=texto, **kwargs)


def labelframe(parent, texto, **kw):
    """LabelFrame con el estilo del sistema (fondo y tipografía)."""
    kw.setdefault("bg", FONDO)
    kw.setdefault("fg", TEXTO)
    kw.setdefault("font", (FUENTE, 11, "bold"))
    kw.setdefault("relief", "groove")
    kw.setdefault("bd", 1)
    return tk.LabelFrame(parent, text=texto, **kw)


def contenido_scrollable(panel):
    """
    Convierte un panel en contenedor con scroll vertical.
    """
    fondo = panel.cget("bg")
    exterior = tk.Frame(panel, bg=fondo)
    exterior.pack(fill="both", expand=True)
    canvas = tk.Canvas(exterior, bg=fondo, highlightthickness=0)
    barra = ttk.Scrollbar(exterior, orient="vertical", command=canvas.yview)
    contenido = tk.Frame(canvas, bg=fondo)
    contenido.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    ventana = canvas.create_window((0, 0), window=contenido, anchor="nw")
    canvas.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfigure(ventana, width=e.width))
    panel.canvas_scroll = canvas
    return contenido
