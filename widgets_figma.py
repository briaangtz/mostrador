# -*- coding: utf-8 -*-
"""
Widgets del diseño Figma, en Tkinter puro (sin librerías extra):

  Tarjeta : contenedor con esquinas redondeadas y borde fino. Se usa
            poniendo los widgets dentro de  tarjeta.cuerpo
  Boton   : botón redondeado con icono + texto, hover y estado deshabilitado
            (misma idea que st.BotonAccion: configurar_estado(...))
"""

import tkinter as tk
import tkinter.font as tkfont

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
        if h != int(tk.Canvas.cget(self, "height")):
            tk.Canvas.configure(self, height=h)

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
            tk.Canvas.configure(self, bg=exterior)
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


class ItemNav(tk.Frame):
    """Ítem del menú lateral: icono + texto, hover, y barrita azul si está activo."""

    def __init__(self, parent, texto, icono, comando):
        super().__init__(parent, bg=st.SIDEBAR)
        self.comando = comando
        self.activo = False
        self._hover = False
        self._img_n = ic.icono(icono, 20, "#A9B7CE", 1.7)
        self._img_a = ic.icono(icono, 20, "#FFFFFF", 1.7)

        self.barra = tk.Frame(self, bg=st.SIDEBAR, width=3)
        self.barra.pack(side="left", fill="y")
        self.pastilla = Tarjeta(self, fondo=st.SIDEBAR, sin_borde=True, radio=9,
                                padx=0, pady=0, alto=38, exterior=st.SIDEBAR)
        self.pastilla.pack(side="left", fill="x", expand=True)
        cu = self.pastilla.cuerpo
        self.ico = tk.Label(cu, image=self._img_n, bg=st.SIDEBAR)
        self.ico.place(x=10, rely=0.5, anchor="w")
        self.txt = tk.Label(cu, text=texto, bg=st.SIDEBAR, fg="#C7D2E4",
                            font=(st.FUENTE, 10))
        self.txt.place(x=42, rely=0.5, anchor="w")

        for w in (self, self.barra, self.pastilla, cu, self.ico, self.txt):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self._clic)
            w.bind("<Enter>", self._entra)
            w.bind("<Leave>", self._sale)

    def _clic(self, _e=None):
        if self.comando:
            self.comando()

    def _entra(self, _e=None):
        self._hover = True
        self._pintar()

    def _sale(self, _e=None):
        try:  # si el mouse sigue sobre un hijo de este ítem, no es una salida real
            x, y = self.winfo_pointerxy()
            w = self.winfo_containing(x, y)
            if w is not None and (str(w) == str(self)
                                  or str(w).startswith(str(self) + ".")):
                return
        except Exception:
            pass
        self._hover = False
        self._pintar()

    def set_activo(self, activo):
        self.activo = bool(activo)
        self._pintar()

    def _pintar(self):
        if self.activo:
            fondo, fg, img, fuente = st.SIDEBAR_ACTIVO, "#FFFFFF", self._img_a, (st.FUENTE, 10, "bold")
        elif self._hover:
            fondo, fg, img, fuente = st.SIDEBAR_HOVER, "#E5ECF8", self._img_a, (st.FUENTE, 10)
        else:
            fondo, fg, img, fuente = st.SIDEBAR, "#C7D2E4", self._img_n, (st.FUENTE, 10)
        self.pastilla.pintar(fondo=fondo)
        self.ico.configure(bg=fondo, image=img)
        self.txt.configure(bg=fondo, fg=fg, font=fuente)
        self.barra.configure(bg=st.ACENTO if self.activo else st.SIDEBAR)


class Pildora(Tarjeta):
    """Píldora de estado con punto de color (Abierta / Cerrada)."""

    def __init__(self, parent, texto, fondo, color, exterior="#FFFFFF",
                 ancho=98, alto=32):
        super().__init__(parent, fondo=fondo, sin_borde=True, radio=alto // 2,
                         padx=0, pady=0, alto=alto, ancho=ancho,
                         exterior=exterior)
        self._inner = tk.Frame(self.cuerpo, bg=fondo)
        self._inner.place(relx=0.5, rely=0.5, anchor="center")
        self.lbl_punto = tk.Label(self._inner, text="\u25cf", bg=fondo, fg=color,
                                  font=(st.FUENTE, 8))
        self.lbl_punto.pack(side="left", padx=(0, 6))
        self.lbl = tk.Label(self._inner, text=texto, bg=fondo, fg=color,
                            font=(st.FUENTE, 10, "bold"))
        self.lbl.pack(side="left")

    def set(self, texto, fondo, color):
        self.pintar(fondo=fondo)
        self._inner.configure(bg=fondo)
        self.lbl_punto.configure(bg=fondo, fg=color)
        self.lbl.configure(text=texto, bg=fondo, fg=color)


class Btn(Tarjeta):
    """Botón redondeado que se usa como un tk.Button de siempre.

    Acepta text, command, bg, fg, font, padx, pady y state, y también
    .config(text=..., bg=..., state=...), así la lógica existente no cambia.
    El hover (un tono más oscuro) lo maneja solo.
    """

    def __init__(self, parent, text="", command=None, bg=None, fg="#FFFFFF",
                 font=None, padx=14, pady=8, state="normal", radio=9, **_):
        self._b_texto = text
        self._b_cmd = command
        self._b_color = bg or st.ACENTO
        self._b_fg = fg
        self._b_font = font or (st.FUENTE, 10, "bold")
        self._b_px = padx
        self._b_py = pady
        self._b_estado = state
        self._b_hover = False
        try:
            exterior = parent.cget("bg")
        except tk.TclError:
            exterior = st.FONDO
        ancho, alto = self._medir()
        super().__init__(parent, fondo=self._b_color, sin_borde=True,
                         radio=radio, padx=0, pady=0, alto=alto, ancho=ancho,
                         exterior=exterior)
        self._b_lbl = tk.Label(self.cuerpo, text=text, bg=self._b_color,
                               fg=fg, font=self._b_font)
        self._b_lbl.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self, self.cuerpo, self._b_lbl):
            w.bind("<Button-1>", self._b_clic)
            w.bind("<Enter>", self._b_entra)
            w.bind("<Leave>", self._b_sale)
        self._b_aplicar()

    # --- tamaño según el texto ---
    def _medir(self):
        f = tkfont.Font(font=self._b_font)
        return (f.measure(self._b_texto) + 2 * self._b_px + 4,
                f.metrics("linespace") + 2 * self._b_py)

    # --- eventos ---
    def _b_clic(self, _e=None):
        if self._b_estado != "disabled" and self._b_cmd:
            self._b_cmd()

    def _b_entra(self, _e=None):
        self._b_hover = True
        self._b_aplicar()

    def _b_sale(self, _e=None):
        self._b_hover = False
        self._b_aplicar()

    def _b_aplicar(self):
        bg = self._b_color
        if self._b_estado != "disabled" and self._b_hover:
            bg = _oscurecer(bg, 0.88)
        Tarjeta.pintar(self, fondo=bg)
        self._b_lbl.configure(bg=bg, fg=self._b_fg, text=self._b_texto,
                              font=self._b_font)
        cur = "arrow" if self._b_estado == "disabled" else "hand2"
        tk.Canvas.configure(self, cursor=cur)
        self.cuerpo.configure(cursor=cur)
        self._b_lbl.configure(cursor=cur)

    # --- compatibilidad con tk.Button ---
    def configure(self, cnf=None, **kw):
        if cnf:
            kw = {**cnf, **kw}
        medir = False
        for k in list(kw):
            if k in ("bg", "background"):
                self._b_color = kw.pop(k)
            elif k in ("fg", "foreground"):
                self._b_fg = kw.pop(k)
            elif k == "text":
                self._b_texto = kw.pop(k)
                medir = True
            elif k == "state":
                self._b_estado = kw.pop(k)
            elif k == "command":
                self._b_cmd = kw.pop(k)
            elif k == "font":
                self._b_font = kw.pop(k)
                medir = True
            elif k == "padx":
                self._b_px = kw.pop(k)
                medir = True
            elif k == "pady":
                self._b_py = kw.pop(k)
                medir = True
            elif k in ("activebackground", "activeforeground", "relief", "bd",
                       "borderwidth", "overrelief"):
                kw.pop(k)
        if kw:
            tk.Canvas.configure(self, **kw)
        if medir:
            ancho, alto = self._medir()
            tk.Canvas.configure(self, width=ancho, height=alto)
        self._b_aplicar()

    config = configure

    def cget(self, key):
        if key == "text":
            return self._b_texto
        if key == "state":
            return self._b_estado
        if key in ("bg", "background"):
            return self._b_color
        return super().cget(key)

    def invoke(self):
        self._b_clic()


class Aviso(Tarjeta):
    """Franja de aviso redondeada (por ejemplo "CAJA CERRADA")."""

    def __init__(self, parent, fondo="#FDEEEE", borde="#F5C2C2", color=None,
                 icono="lock"):
        try:
            exterior = parent.cget("bg")
        except tk.TclError:
            exterior = st.FONDO
        super().__init__(parent, fondo=fondo, borde=borde, radio=12,
                         padx=16, pady=11, exterior=exterior)
        color = color or st.ROJO
        fila = tk.Frame(self.cuerpo, bg=fondo)
        fila.pack(fill="x")
        tk.Label(fila, image=ic.icono(icono, 20, color, 1.8),
                 bg=fondo).pack(side="left", padx=(0, 10))
        self.lbl = tk.Label(fila, text="", bg=fondo, fg=color,
                            font=(st.FUENTE, 10, "bold"), justify="left",
                            anchor="w")
        self.lbl.pack(side="left", fill="x", expand=True)
        fila.bind("<Configure>", lambda e: self.lbl.configure(
            wraplength=max(120, e.width - 40)))

    def set(self, text=None, **_):
        if text is not None:
            self.lbl.configure(text=text)
