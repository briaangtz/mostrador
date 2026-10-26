# -*- coding: utf-8 -*-
"""
Widgets del diseño Figma, en Tkinter puro (sin librerías extra):

  Tarjeta : contenedor con esquinas redondeadas y borde fino. Se usa
            poniendo los widgets dentro de  tarjeta.cuerpo
  Boton   : botón redondeado con icono + texto, hover y estado deshabilitado
            (misma idea que st.BotonAccion: configurar_estado(...))
"""

import tkinter as tk

import estilos as st
import iconos as ic

_SIN = object()


def _oscurecer(color, f=0.88):
    try:
        h = color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))
    except Exception:
        return color


class Tarjeta(tk.Canvas):
    """Tarjeta redondeada. El alto se ajusta solo al contenido de .cuerpo."""

    def __init__(self, parent, fondo=None, borde=None, radio=12, padx=20,
                 pady=16, alto=None, ancho=1, exterior=None, sin_borde=False):
        # OJO: no usar nombres _w, _name, etc. (los usa tkinter por dentro)
        self.fondo = fondo or st.TARJETA
        self.borde = None if sin_borde else (borde or st.BORDE)
        self.radio = radio
        # El contenido nunca debe tapar las esquinas redondeadas
        inset = int(radio * 0.30) + 2
        self.padx = max(padx, inset)
        self.pady = max(pady, inset)
        padx, pady = self.padx, self.pady
        self.alto_fijo = alto
        self._exterior = exterior or st.FONDO
        self._ancho_px = 0
        self._alto_px = 0
        super().__init__(parent, bg=self._exterior, highlightthickness=0, bd=0,
                         width=ancho, height=alto or 20)
        self.cuerpo = tk.Frame(self, bg=self.fondo)
        self._ventana = self.create_window(padx, pady, window=self.cuerpo,
                                           anchor="nw")
        self.bind("<Configure>", self._al_cambiar)
        if alto is None:
            self.cuerpo.bind("<Configure>", self._ajustar_alto)

    # ------------------------------------------------------------ tamaño
    def _al_cambiar(self, e):
        w, h = e.width, e.height
        if w < 4 or h < 4 or (w, h) == (self._ancho_px, self._alto_px):
            return
        self._ancho_px, self._alto_px = w, h
        self.itemconfigure(self._ventana, width=max(1, w - 2 * self.padx))
        if self.alto_fijo:
            self.itemconfigure(self._ventana, height=max(1, h - 2 * self.pady))
        self.redibujar()

    def _ajustar_alto(self, _e=None):
        h = self.cuerpo.winfo_reqheight() + 2 * self.pady
        if h != int(self.cget("height")):
            self.configure(height=h)

    # ------------------------------------------------------------ dibujo
    def redibujar(self):
        w, h = self._ancho_px, self._alto_px
        if w < 4 or h < 4:
            return
        self.delete("fondo")
        r = max(2, min(self.radio, h // 2, w // 2))
        b, f = self.borde, self.fondo
        if b:
            self.create_rectangle(r, 0, w - r, h, fill=b, outline="", tags="fondo")
            self.create_rectangle(0, r, w, h - r, fill=b, outline="", tags="fondo")
            self.create_rectangle(r, 1, w - r, h - 1, fill=f, outline="", tags="fondo")
            self.create_rectangle(1, r, w - 1, h - r, fill=f, outline="", tags="fondo")
        else:
            self.create_rectangle(r, 0, w - r, h, fill=f, outline="", tags="fondo")
            self.create_rectangle(0, r, w, h - r, fill=f, outline="", tags="fondo")
        tiles = ic.esquinas(r, f, b)
        for t, (x, y) in zip(tiles, ((0, 0), (w - r, 0), (0, h - r), (w - r, h - r))):
            self.create_image(x, y, image=t, anchor="nw", tags="fondo")
        self.tag_lower("fondo")

    def pintar(self, fondo=None, borde=_SIN, exterior=None):
        """Cambia colores en caliente (por ejemplo abierta/cerrada)."""
        if fondo:
            self.fondo = fondo
            self.cuerpo.configure(bg=fondo)
        if borde is not _SIN:
            self.borde = borde
        if exterior:
            self._exterior = exterior
            self.configure(bg=exterior)
        self.redibujar()


class Boton(Tarjeta):
    """Botón redondeado con icono blanco + texto."""

    GRIS = "#94A3B8"

    def __init__(self, parent, texto, color, comando, icono=None, alto=48,
                 radio=10, ancho=1, exterior=None, tam=12):
        super().__init__(parent, fondo=color, sin_borde=True, radio=radio,
                         padx=0, pady=0, alto=alto, ancho=ancho,
                         exterior=exterior)
        self.color = color
        self.comando = comando
        self.habilitado = True
        self._img = ic.icono(icono, 20, "#FFFFFF", 1.9) if icono else None
        self.lbl = tk.Label(self.cuerpo, text=self._fmt(texto),
                            image=self._img if self._img else "",
                            compound="left", bg=color, fg="#FFFFFF",
                            font=(st.FUENTE, tam, "bold"), cursor="hand2")
        self.lbl.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self, self.cuerpo, self.lbl):
            w.bind("<Button-1>", self._clic)
            w.bind("<Enter>", self._entra)
            w.bind("<Leave>", self._sale)
        self.configure(cursor="hand2")

    def _fmt(self, texto):
        return ("  " + texto) if self._img is not None else texto

    def _clic(self, _e=None):
        if self.habilitado and self.comando:
            self.comando()

    def _entra(self, _e=None):
        if self.habilitado:
            self.pintar(fondo=_oscurecer(self.color))

    def _sale(self, _e=None):
        self.pintar(fondo=self.color if self.habilitado else self.GRIS)

    def pintar(self, fondo=None, borde=_SIN, exterior=None):
        super().pintar(fondo=fondo, borde=borde, exterior=exterior)
        if fondo:
            self.lbl.configure(bg=fondo)

    def configurar_estado(self, habilitado, texto=None, color=None):
        """Misma firma que st.BotonAccion.configurar_estado."""
        self.habilitado = bool(habilitado)
        if color and habilitado:
            self.color = color
        if texto is not None:
            self.lbl.configure(text=self._fmt(texto))
        cursor = "hand2" if self.habilitado else "arrow"
        self.configure(cursor=cursor)
        self.lbl.configure(cursor=cursor)
        self.pintar(fondo=self.color if self.habilitado else self.GRIS)
