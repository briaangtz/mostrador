# -*- coding: utf-8 -*-
"""Estilos y widgets reutilizables de la interfaz."""

import tkinter as tk
from tkinter import ttk

# Paleta de colores
FONDO = "#eef2f7"
TARJETA = "#ffffff"
BORDE = "#dde3ea"
BARRA = "#16213e"
BARRA_TEXTO = "#ffffff"
ACENTO = "#2563eb"
ACENTO_OSCURO = "#1d4ed8"
TEXTO = "#111827"
TEXTO_SUAVE = "#6b7280"
VERDE = "#16a34a"
VERDE_OSCURO = "#15803d"
ROJO = "#dc2626"
AMBAR = "#d97706"
ROJO_CLARO = "#fee2e2"
VERDE_CLARO = "#dcfce7"
AMBAR_CLARO = "#fef3c7"

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
                    font=(FUENTE, 20, "bold"))
    style.configure("Subtitulo.TLabel", background=FONDO, foreground=TEXTO_SUAVE,
                    font=(FUENTE, 11))
    style.configure("Encabezado.TLabelframe", background=FONDO, foreground=TEXTO,
                    font=(FUENTE, 11, "bold"))
    style.configure("Encabezado.TLabelframe.Label", background=FONDO,
                    foreground=TEXTO, font=(FUENTE, 11, "bold"))
    style.configure("CardEncabezado.TLabel", background=TARJETA,
                    foreground=TEXTO_SUAVE, font=(FUENTE, 9))
    style.configure("CardValor.TLabel", background=TARJETA, foreground=TEXTO,
                    font=(FUENTE, 16, "bold"))
    style.configure("CardValorChico.TLabel", background=TARJETA, foreground=TEXTO,
                    font=(FUENTE, 13, "bold"))
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

    style.configure("Treeview", font=(FUENTE, 10), rowheight=26,
                    background="#ffffff", fieldbackground="#ffffff", foreground=TEXTO)
    style.configure("Treeview.Heading", font=(FUENTE, 10, "bold"),
                    background="#e5eaf1", foreground=TEXTO)
    style.map("Treeview", background=[("selected", ACENTO)],
              foreground=[("selected", "#ffffff")])

    style.configure("TCombobox", padding=(6, 4))
    style.configure("TSpinbox", padding=(6, 4))
    style.configure("Labelframe", background=FONDO)
    return style


def tarjeta(parent, titulo, valor_inicial="—", ancho_chico=False, detalle=""):
    """Crea una tarjeta de resumen. Devuelve (frame, etiqueta_valor).

    La etiqueta de detalle (texto chico debajo del valor, por ejemplo el
    desglose de Tarjetas) queda en frame.lbl_detalle.
    """
    frame = tk.Frame(parent, bg=TARJETA, bd=0, highlightbackground=BORDE,
                     highlightthickness=1)
    lbl_t = tk.Label(frame, text=titulo.upper(), bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 8, "bold"), anchor="w")
    lbl_t.pack(fill="x", padx=12, pady=(8, 0))
    lbl_v = tk.Label(frame, text=valor_inicial, bg=TARJETA, fg=TEXTO,
                     font=(FUENTE, 14 if ancho_chico else 17, "bold"), anchor="w")
    lbl_v.pack(fill="x", padx=12, pady=(2, 0))
    lbl_d = tk.Label(frame, text=detalle, bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 8), anchor="w")
    lbl_d.pack(fill="x", padx=12, pady=(0, 8))
    frame.lbl_detalle = lbl_d
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
    Convierte un panel en contenedor con scroll vertical: devuelve el frame
    donde hay que empacar el contenido (en vez de empacar en el panel).

    Así ningún contenido queda cortado ni oculto en pantallas chicas, y en
    pantallas grandes se aprovecha todo el espacio. La rueda del mouse la
    maneja main.App._rueda_global (mira panel.canvas_scroll).
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
