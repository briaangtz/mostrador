# -*- coding: utf-8 -*-
"""Estilos y widgets reutilizables para la interfaz GARRAFAS.

Diseño fiel a la especificación "Caja del Día":
- Sidebar #0B1E45, barra superior #0A1A3A, contenido #F3F6FB.
- Tarjetas blancas con esquinas redondeadas y sombra suave vía Canvas.
- Iconos de línea dibujados en Canvas (estilo Lucide/Feather), sin emojis.
- Fuente: Segoe UI.
"""

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Paleta de colores (especificación exacta)
# ---------------------------------------------------------------------------
BARRA = "#0B1E45"           # Azul marino sidebar
BARRA_SUPERIOR = "#0A1A3A"  # Azul marino muy oscuro barra superior
FONDO = "#F3F6FB"           # Fondo del contenido
TARJETA = "#FFFFFF"         # Tarjetas blancas
BORDE = "#E2E8F0"           # Borde sutil

ACENTO = "#2563EB"          # Azul activo / botón principal
ACENTO_OSCURO = "#1D4ED8"   # Azul más oscuro (hover / activo)
VERDE = "#0E9A55"           # Verde (abierta, éxito)
VERDE_OSCURO = "#0B7A45"
ROJO = "#DC2626"
AMBAR = "#F59E0B"           # Naranja / ámbar
AMBAR_CLARO = "#FEF3C7"     # Ámbar claro (banner avisos)
CELESTE = "#3B82F6"         # Celeste
TURQUESA = "#14B8A6"        # Turquesa
VIOLETA = "#7C3AED"         # Violeta
ROJO_CLARO = "#FEE2E2"
VERDE_CLARO = "#DCFCE7"

# Colores del diseño Figma (barra lateral y barra superior)
SIDEBAR = "#101E35"          # Fondo de la barra lateral
SIDEBAR_ACTIVO = "#213D66"   # Ítem activo del menú
SIDEBAR_HOVER = "#182B4A"    # Ítem con el mouse encima
SIDEBAR_TARJETA = "#0C1729"  # Tarjeta de datos de caja (abajo)
BARRA_BORDE = "#E2E7EF"      # Línea bajo la barra superior blanca

TEXTO = "#0F1F3D"           # Texto principal oscuro
TEXTO_SUAVE = "#64748B"     # Texto secundario gris azulado
BLANCO = "#FFFFFF"

# Colores de íconos por medio de pago (tarjetas de métrica)
COLOR_GARRAFA = ACENTO      # Azul
COLOR_TOTAL = VERDE         # Verde
COLOR_EFECTIVO = VIOLETA    # Violeta
COLOR_TRANS = CELESTE       # Celeste
COLOR_TARJETA = AMBAR       # Naranja
COLOR_BONO = "#BE185D"      # Rosa
COLOR_VENTAS = VIOLETA      # Violeta

FUENTE = "Segoe UI"

# ---------------------------------------------------------------------------
# Utilidades de dibujo con Canvas (bordes redondeados, sombras, iconos)
# ---------------------------------------------------------------------------
def _redondeado(canvas, x, y, w, h, r, fill=None, outline=None, width=0, tags=()):
    """Dibuja un rectángulo con esquinas redondeadas en un Canvas."""
    puntos = [
        x + r, y,
        x + w - r, y,
        x + w, y,
        x + w, y + r,
        x + w, y + h - r,
        x + w, y + h,
        x + w - r, y + h,
        x + r, y + h,
        x, y + h,
        x, y + h - r,
        x, y + r,
        x, y,
    ]
    return canvas.create_polygon(
        puntos, smooth=True, fill=fill, outline=outline,
        width=width, tags=tags)


def _circulo(canvas, x, y, r, fill=None, outline=None, width=0, tags=()):
    """Dibuja un círculo."""
    return canvas.create_oval(
        x - r, y - r, x + r, y + r,
        fill=fill, outline=outline, width=width, tags=tags)


def _linea(canvas, x1, y1, x2, y2, color="#64748B", grosor=2, tags=()):
    """Dibuja una línea."""
    return canvas.create_line(
        x1, y1, x2, y2, fill=color, width=grosor,
        capstyle=tk.ROUND, tags=tags)


# ---------------------------------------------------------------------------
# Tarjeta de métrica con Canvas (fondo blanco, borde redondeado, sombra)
# ---------------------------------------------------------------------------
class TarjetaMetrica(tk.Canvas):
    """Tarjeta blanca con esquina redondeada ~12px, sombra suave,
    ícono circular de color a la izquierda, etiqueta y valor."""

    def __init__(self, parent, titulo, valor, color_icono, detalle="",
                 ancho=230, alto=110, radio=12, fuente_valor=18):
        super().__init__(
            parent, width=ancho, height=alto,
            highlightthickness=0, bd=0, bg=parent.cget("bg")
        )
        self.ancho = ancho
        self.alto = alto
        self.radio = radio
        self.color_icono = color_icono
        self.titulo = titulo
        self.valor_actual = valor
        self.detalle_actual = detalle
        self.fuente_valor = fuente_valor

        # Sombra suave (desplazada)
        self.sombra = _redondeado(
            self, 3, 3, ancho - 6, alto - 6, radio,
            fill="#DDE3EA", outline="", tags=("sombra",))
        # Tarjeta blanca
        self.fondo = _redondeado(
            self, 0, 0, ancho - 3, alto - 3, radio,
            fill=TARJETA, outline=BORDE, width=1, tags=("fondo",))

        # Ícono circular de color (izquierda)
        cx = 26
        cy = alto // 2
        r_icono = 16
        self.icono_circulo = _circulo(
            self, cx, cy, r_icono, fill=color_icono, outline="", tags=("icono",))
        self.icono_linea = None  # se dibuja después

        # Etiqueta (mayúsculas, chica, gris azulada)
        self.lbl_titulo = self.create_text(
            cx + r_icono + 14, cy - 26,
            text=titulo.upper(), fill=TEXTO_SUAVE,
            font=(FUENTE, 9, "bold"), anchor="w", tags=("titulo",))
        # Valor (grande, negrita)
        self.lbl_valor = self.create_text(
            cx + r_icono + 14, cy + 2,
            text=valor, fill=TEXTO,
            font=(FUENTE, fuente_valor, "bold"), anchor="w", tags=("valor",))
        # Detalle (chico, debajo del valor)
        self.lbl_detalle = self.create_text(
            cx + r_icono + 14, cy + 26,
            text=detalle, fill=TEXTO_SUAVE,
            font=(FUENTE, 8), anchor="w", tags=("detalle",))

        # Dibujar icono de línea según el tipo
        self._dibujar_icono(titulo)

    def _dibujar_icono(self, titulo):
        """Dibuja el icono de línea dentro del círculo."""
        cx = 26
        cy = self.alto // 2
        r = 16
        color = BLANCO
        grosor = 2
        self.delete("icono_linea")
        t = titulo.upper()
        if t.startswith("GARRAFAS"):
            # Garrafa: trapecio + tapa
            self._linea(cx - 8, cy + 8, cx + 8, cy + 8, color, grosor, "icono_linea")
            self._linea(cx - 6, cy + 8, cx - 10, cy - 4, color, grosor, "icono_linea")
            self._linea(cx + 6, cy + 8, cx + 10, cy - 4, color, grosor, "icono_linea")
            self._linea(cx - 10, cy - 4, cx + 10, cy - 4, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 4, cx - 6, cy - 10, color, grosor, "icono_linea")
            self._linea(cx + 6, cy - 4, cx + 6, cy - 10, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 10, cx + 6, cy - 10, color, grosor, "icono_linea")
        elif t.startswith("TOTAL"):
            # Símbolo $
            self._linea(cx - 8, cy - 8, cx + 8, cy - 8, color, grosor, "icono_linea")
            self._linea(cx - 8, cy + 8, cx + 8, cy + 8, color, grosor, "icono_linea")
            self._linea(cx, cy - 8, cx, cy + 8, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 2, cx + 6, cy - 2, color, grosor, "icono_linea")
            self._linea(cx - 6, cy + 2, cx + 6, cy + 2, color, grosor, "icono_linea")
        elif t.startswith("EFECTIVO"):
            # Caja registradora: rectángulo con línea superior
            self._linea(cx - 9, cy - 9, cx + 9, cy - 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy - 9, cx - 9, cy + 6, color, grosor, "icono_linea")
            self._linea(cx + 9, cy - 9, cx + 9, cy + 6, color, grosor, "icono_linea")
            self._linea(cx - 9, cy + 6, cx + 9, cy + 6, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 4, cx + 6, cy - 4, color, grosor, "icono_linea")
        elif t.startswith("TRANSFERENCIAS"):
            # Tarjeta/banco: rectángulo con chip
            self._linea(cx - 9, cy - 9, cx + 9, cy - 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy - 9, cx - 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx + 9, cy - 9, cx + 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy + 9, cx + 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx - 7, cy - 5, cx - 3, cy - 5, color, grosor, "icono_linea")
            self._linea(cx - 7, cy - 1, cx - 3, cy - 1, color, grosor, "icono_linea")
            self._linea(cx - 7, cy + 3, cx - 3, cy + 3, color, grosor, "icono_linea")
        elif t.startswith("TARJETAS"):
            # Tarjeta con banda
            self._linea(cx - 9, cy - 9, cx + 9, cy - 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy - 9, cx - 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx + 9, cy - 9, cx + 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy + 9, cx + 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy - 2, cx + 9, cy - 2, color, grosor, "icono_linea")
        elif t.startswith("TOTAL GENERAL"):
            # Documento con líneas
            self._linea(cx - 9, cy - 9, cx + 6, cy - 9, color, grosor, "icono_linea")
            self._linea(cx + 6, cy - 9, cx + 9, cy - 6, color, grosor, "icono_linea")
            self._linea(cx + 9, cy - 6, cx + 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx + 9, cy + 9, cx - 9, cy + 9, color, grosor, "icono_linea")
            self._linea(cx - 9, cy + 9, cx - 9, cy - 9, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 5, cx + 4, cy - 5, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 1, cx + 4, cy - 1, color, grosor, "icono_linea")
            self._linea(cx - 6, cy + 3, cx + 4, cy + 3, color, grosor, "icono_linea")
        elif t.startswith("VENTAS REGISTRADAS"):
            # Portapapeles
            self._linea(cx - 8, cy - 9, cx + 8, cy - 9, color, grosor, "icono_linea")
            self._linea(cx - 8, cy - 9, cx - 8, cy + 6, color, grosor, "icono_linea")
            self._linea(cx + 8, cy - 9, cx + 8, cy + 6, color, grosor, "icono_linea")
            self._linea(cx - 8, cy + 6, cx + 8, cy + 6, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 7, cx + 6, cy - 7, color, grosor, "icono_linea")
            self._linea(cx - 6, cy - 3, cx + 6, cy - 3, color, grosor, "icono_linea")
            self._linea(cx - 6, cy + 1, cx + 6, cy + 1, color, grosor, "icono_linea")

    def _linea(self, x1, y1, x2, y2, color, grosor, tag):
        return _linea(self, x1, y1, x2, y2, color, grosor, tag)

    def actualizar_valor(self, valor, detalle=None):
        self.itemconfig(self.lbl_valor, text=valor)
        self.valor_actual = valor
        if detalle is not None:
            self.itemconfig(self.lbl_detalle, text=detalle)
            self.detalle_actual = detalle


# ---------------------------------------------------------------------------
# Botón grande de acción con Canvas (fondo color, texto blanco, icono)
# ---------------------------------------------------------------------------
class BotonAccion(tk.Canvas):
    """Botón grande con fondo de color, texto blanco y borde redondeado."""

    def __init__(self, parent, texto, color, comando, ancho=260, alto=76,
                 radio=10, icono_texto="", fuente=(FUENTE, 13, "bold")):
        super().__init__(
            parent, width=ancho, height=alto,
            highlightthickness=0, bd=0, bg=parent.cget("bg")
        )
        self.ancho = ancho
        self.alto = alto
        self.color = color
        self.comando = comando
        self.radio = radio
        self.activo = True

        # Fondo redondeado
        self.fondo = _redondeado(
            self, 0, 0, ancho, alto, radio, fill=color, outline="", tags=("fondo",))
        # Texto + icono centrados
        self.lbl_texto = self.create_text(
            ancho // 2, alto // 2,
            text=f"{icono_texto}  {texto}" if icono_texto else texto,
            fill=BLANCO, font=fuente, anchor="center", tags=("texto",))

        # Eventos
        self.bind("<Button-1>", self._clic)
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)

    def _clic(self, evento):
        if self.activo and self.comando:
            self.comando()

    def _entrar(self, evento):
        if self.activo:
            self.itemconfig(self.fondo, fill=ACENTO_OSCURO if self.color == ACENTO else VERDE_OSCURO)

    def _salir(self, evento):
        if self.activo:
            self.itemconfig(self.fondo, fill=self.color)

    def configurar_estado(self, activo, texto=None, color=None):
        self.activo = activo
        if texto is not None:
            self.itemconfig(self.lbl_texto, text=texto)
        if color is not None:
            self.color = color
            self.itemconfig(self.fondo, fill=color if activo else "#94a3b8")
            self.itemconfig(self.lbl_texto, fill=BLANCO if activo else "#cbd5e1")


# ---------------------------------------------------------------------------
# Estilos ttk (mínimos, solo para Combobox si es necesario)
# ---------------------------------------------------------------------------
def aplicar_estilo(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=(FUENTE, 10), background=FONDO, foreground=TEXTO)
    # Barra de scroll fina, sin flechas (estilo del diseño)
    style.layout("Fino.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Fino.Vertical.TScrollbar", troughcolor=FONDO,
                    background="#C5CEDD", bordercolor=FONDO,
                    lightcolor="#C5CEDD", darkcolor="#C5CEDD",
                    relief="flat", width=9, arrowsize=9)
    style.map("Fino.Vertical.TScrollbar",
              background=[("pressed", "#8794AD"), ("active", "#9AA8BF")])

    # Barras de scroll de todo el programa: finas y sin flechas
    for o in ("Vertical", "Horizontal"):
        nom = f"{o}.TScrollbar"
        style.layout(nom, [(f"{o}.Scrollbar.trough", {"sticky": "nswe", "children": [
            (f"{o}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        style.configure(nom, troughcolor=FONDO, background="#D5DCE8",
                        bordercolor=FONDO, lightcolor="#D5DCE8",
                        darkcolor="#D5DCE8", relief="flat", width=8, arrowsize=8)
        style.map(nom, background=[("pressed", "#8794AD"), ("active", "#B3BFD2")])

    # Campos desplegables y numéricos
    for nom in ("TCombobox", "TSpinbox", "TEntry"):
        style.configure(nom, fieldbackground="#FFFFFF", background="#FFFFFF",
                        foreground=TEXTO, bordercolor="#D9E0EC",
                        lightcolor="#D9E0EC", darkcolor="#D9E0EC",
                        arrowcolor=TEXTO_SUAVE, insertcolor=TEXTO,
                        padding=(8, 7), relief="flat")
        style.map(nom,
                  fieldbackground=[("disabled", "#F1F5F9"), ("readonly", "#FFFFFF")],
                  foreground=[("disabled", TEXTO_SUAVE)],
                  bordercolor=[("focus", ACENTO)],
                  lightcolor=[("focus", ACENTO)],
                  darkcolor=[("focus", ACENTO)])
    style.map("TCombobox",
              selectbackground=[("readonly", "#FFFFFF")],
              selectforeground=[("readonly", TEXTO)])
    root.option_add("*TCombobox*Listbox.font", (FUENTE, 10))
    root.option_add("*TCombobox*Listbox.selectBackground", "#DBEAFE")
    root.option_add("*TCombobox*Listbox.selectForeground", TEXTO)
    root.option_add("*TCombobox*Listbox.background", "#FFFFFF")

    # Pestañas
    style.configure("TNotebook", background=FONDO, borderwidth=0,
                    bordercolor=FONDO, lightcolor=FONDO, darkcolor=FONDO,
                    tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background="#E3E9F3",
                    foreground=TEXTO_SUAVE, padding=(18, 10), borderwidth=0,
                    bordercolor="#E3E9F3", lightcolor="#E3E9F3",
                    darkcolor="#E3E9F3", font=(FUENTE, 10, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", "#FFFFFF"), ("active", "#EDF1F8")],
              foreground=[("selected", ACENTO_OSCURO)],
              lightcolor=[("selected", "#FFFFFF")],
              darkcolor=[("selected", "#FFFFFF")],
              bordercolor=[("selected", "#FFFFFF")],
              padding=[("selected", (18, 10))],
              expand=[("selected", (0, 0, 0, 0))])

    # Tablas
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                    foreground=TEXTO, rowheight=30, borderwidth=0,
                    font=(FUENTE, 10))
    style.map("Treeview", background=[("selected", "#DBEAFE")],
              foreground=[("selected", TEXTO)])
    style.configure("Treeview.Heading", background="#F1F5F9",
                    foreground=TEXTO_SUAVE, relief="flat", borderwidth=0,
                    bordercolor="#E2E8F0", lightcolor="#F1F5F9",
                    darkcolor="#F1F5F9", font=(FUENTE, 9, "bold"),
                    padding=(8, 8))
    style.map("Treeview.Heading", background=[("active", "#E8EEF7")])
    return style


def contenido_scrollable(panel):
    """Panel con scroll vertical, barra superior y sidebar quedan fijas."""
    fondo = panel.cget("bg")
    exterior = tk.Frame(panel, bg=fondo)
    exterior.pack(fill="both", expand=True)
    canvas = tk.Canvas(exterior, bg=fondo, highlightthickness=0)
    barra = ttk.Scrollbar(exterior, orient="vertical", command=canvas.yview,
                          style="Fino.Vertical.TScrollbar")
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


def etiqueta(parent, texto, **kwargs):
    return tk.Label(parent, text=texto, **kwargs)


def labelframe(parent, texto, **kw):
    kw.setdefault("bg", FONDO)
    kw.setdefault("fg", TEXTO)
    kw.setdefault("font", (FUENTE, 11, "bold"))
    kw.setdefault("relief", "groove")
    kw.setdefault("bd", 1)
    return tk.LabelFrame(parent, text=texto, **kw)


def tarjeta_simple(parent, titulo, valor_inicial="—", detalle=""):
    """Tarjeta simple (Frame) para pantallas secundarias como Estadísticas."""
    frame = tk.Frame(parent, bg=TARJETA, bd=0,
                     highlightbackground=BORDE, highlightthickness=1)
    lbl_t = tk.Label(frame, text=titulo.upper(), bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 9, "bold"), anchor="w")
    lbl_t.pack(fill="x", padx=12, pady=(8, 0))
    lbl_v = tk.Label(frame, text=valor_inicial, bg=TARJETA, fg=TEXTO,
                     font=(FUENTE, 16, "bold"), anchor="w")
    lbl_v.pack(fill="x", padx=12, pady=(2, 0))
    lbl_d = tk.Label(frame, text=detalle, bg=TARJETA, fg=TEXTO_SUAVE,
                     font=(FUENTE, 8), anchor="w")
    lbl_d.pack(fill="x", padx=12, pady=(0, 8))
    frame.lbl_detalle = lbl_d
    frame.lbl_valor = lbl_v
    return frame, lbl_v
