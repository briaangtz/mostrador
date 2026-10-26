# -*- coding: utf-8 -*-
"""
Iconos de línea (estilo Lucide/Feather) dibujados por código con Pillow.

No necesita archivos de imagen: cada icono se genera al vuelo, se suaviza
(antialias) y se guarda en caché. Sirve para toda la interfaz.

Uso:
    import iconos as ic
    img = ic.icono("home", 20, "#FFFFFF")              # icono suelto
    img = ic.cuadro("dollar", 36, "#2563EB", "#E8F0FE")  # icono en cuadro redondeado
    tk.Label(parent, image=img)
"""

import math

from PIL import Image, ImageDraw, ImageFont, ImageTk

_cache = {}


def _fuente(px):
    for f in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, px)
        except OSError:
            continue
    return ImageFont.load_default()


def pil_icono(nombre, px, color, lw=1.8):
    """Devuelve el icono como imagen PIL (RGBA, fondo transparente)."""
    S = 8
    N = px * S
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = N / 24.0
    w = max(2, int(lw * u))

    def P(*pts):
        return [c * u for c in pts]

    def linea(*pts):
        d.line(P(*pts), fill=color, width=w, joint="curve")
        for i in range(0, len(pts), 2):
            x, y = pts[i] * u, pts[i + 1] * u
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color)

    def rrect(x0, y0, x1, y1, r=2):
        d.rounded_rectangle(P(x0, y0, x1, y1), radius=r * u, outline=color, width=w)

    def circulo(cx, cy, r, lleno=False):
        d.ellipse(P(cx - r, cy - r, cx + r, cy + r),
                  outline=None if lleno else color, width=w,
                  fill=color if lleno else None)

    def arco(x0, y0, x1, y1, a0, a1):
        d.arc(P(x0, y0, x1, y1), a0, a1, fill=color, width=w)

    if nombre == "home":
        linea(3, 11.5, 12, 3.5, 21, 11.5)
        linea(5.5, 10, 5.5, 20.5, 18.5, 20.5, 18.5, 10)
        linea(10, 20.5, 10, 14.5, 14, 14.5, 14, 20.5)
    elif nombre == "cart":
        linea(2, 3.5, 5, 3.5, 7.5, 15.5, 19, 15.5, 21, 7.5, 6, 7.5)
        circulo(9.5, 19.5, 1.4)
        circulo(17, 19.5, 1.4)
    elif nombre == "chart":            # estadísticas: barras con tendencia
        linea(4, 21, 4, 15)
        linea(9, 21, 9, 12)
        linea(14, 21, 14, 14)
        linea(19, 21, 19, 8)
        linea(3.5, 11, 8.5, 6.5, 13, 9.5, 20, 3.5)
    elif nombre == "bars":             # ventas por producto
        linea(5, 20, 5, 12)
        linea(12, 20, 12, 5)
        linea(19, 20, 19, 9)
    elif nombre == "gear":
        pts = []
        for i in range(8):
            a = i * 45
            for da, r in ((-11, 7.6), (-7, 10), (7, 10), (11, 7.6)):
                t = math.radians(a + da)
                pts += [12 + r * math.cos(t), 12 + r * math.sin(t)]
        pts += pts[:2]
        linea(*pts)
        circulo(12, 12, 3.2)
    elif nombre == "history":
        arco(3.5, 3.5, 20.5, 20.5, 40, 340)
        linea(2.5, 4, 3.8, 9, 8.5, 7.8)
        linea(12, 7.5, 12, 12.5, 15.5, 14.5)
    elif nombre == "clipboard":
        rrect(5, 4.5, 19, 21.5, 2)
        rrect(9, 2.5, 15, 6.5, 1)
        linea(8.5, 11, 15.5, 11)
        linea(8.5, 15, 15.5, 15)
    elif nombre == "doc":
        rrect(5, 3, 19, 21, 2)
        linea(8.5, 9, 15.5, 9)
        linea(8.5, 13, 15.5, 13)
        linea(8.5, 17, 12.5, 17)
    elif nombre == "grid":
        rrect(3.5, 3.5, 10.5, 10.5, 1.5)
        rrect(13.5, 3.5, 20.5, 10.5, 1.5)
        rrect(3.5, 13.5, 10.5, 20.5, 1.5)
        rrect(13.5, 13.5, 20.5, 20.5, 1.5)
    elif nombre == "user":
        circulo(12, 8, 4)
        arco(4.5, 14, 19.5, 30, 180, 360)
    elif nombre == "calendar":
        rrect(3.5, 5, 20.5, 21, 2.5)
        linea(3.5, 10, 20.5, 10)
        linea(8, 2.5, 8, 7)
        linea(16, 2.5, 16, 7)
        for x in (8, 12, 16):
            circulo(x, 14, 0.6, True)
            circulo(x, 17.5, 0.6, True)
    elif nombre == "chevron":
        linea(6, 9, 12, 15, 18, 9)
    elif nombre == "chevron_right":
        linea(9, 6, 15, 12, 9, 18)
    elif nombre == "dollar":
        d.text((N / 2, N / 2), "$", fill=color, font=_fuente(int(N * 0.95)),
               anchor="mm")
    elif nombre == "cube":
        linea(12, 2.5, 20.5, 7.2, 20.5, 16.8, 12, 21.5, 3.5, 16.8, 3.5, 7.2, 12, 2.5)
        linea(3.5, 7.2, 12, 12, 20.5, 7.2)
        linea(12, 12, 12, 21.5)
    elif nombre == "boxopen":
        linea(3.5, 9.5, 3.5, 17, 12, 21.5, 20.5, 17, 20.5, 9.5)
        linea(12, 14, 12, 21.5)
        linea(3.5, 9.5, 12, 14, 20.5, 9.5)
        linea(3.5, 9.5, 7.5, 3.5, 12, 6.5, 16.5, 3.5, 20.5, 9.5)
        linea(12, 6.5, 12, 14)
    elif nombre == "banknote":
        rrect(2.5, 6, 21.5, 18, 2)
        circulo(12, 12, 2.7)
        circulo(6, 12, 0.6, True)
        circulo(18, 12, 0.6, True)
    elif nombre == "transfer":
        linea(4, 8, 20, 8)
        linea(16, 4, 20, 8, 16, 12)
        linea(20, 16, 4, 16)
        linea(8, 12, 4, 16, 8, 20)
    elif nombre == "card":
        rrect(2.5, 5, 21.5, 19, 2.5)
        linea(2.5, 10, 21.5, 10)
        linea(6, 15, 10, 15)
    elif nombre == "lock":
        rrect(5, 11, 19, 21.5, 2.5)
        arco(7.5, 3, 16.5, 15, 180, 360)
        linea(7.5, 9, 7.5, 11)
        linea(16.5, 9, 16.5, 11)
        circulo(12, 16, 1.2, True)
    elif nombre == "unlock":
        rrect(5, 11, 19, 21.5, 2.5)
        arco(7.5, 1, 16.5, 13, 180, 360)
        linea(7.5, 7, 7.5, 11)
        circulo(12, 16, 1.2, True)
    elif nombre == "info":
        circulo(12, 12, 9.2)
        circulo(12, 7.8, 0.8, True)
        linea(12, 11, 12, 16.5)
    elif nombre == "logout":
        linea(10, 3.5, 5, 3.5, 5, 20.5, 10, 20.5)
        linea(9.5, 12, 20, 12)
        linea(16, 8, 20, 12, 16, 16)
    elif nombre == "flame":            # logo GARRAFAS
        linea(12, 2.8, 16.5, 8, 18.2, 13, 16.2, 18.4, 12, 21,
              7.8, 18.4, 5.8, 13, 7.5, 9.5)
        linea(12, 12.5, 14.2, 15, 14, 17.3, 12, 18.6, 10, 17.3, 9.8, 15, 12, 12.5)
    elif nombre == "garrafa":
        rrect(5.5, 9, 18.5, 22.5, 4)
        linea(5.5, 13.5, 18.5, 13.5)
        rrect(9.5, 5.5, 14.5, 9, 1)
        linea(7.5, 3, 16.5, 3)
        linea(12, 3, 12, 5.5)

    return img.resize((px, px), Image.LANCZOS)


def icono(nombre, px=20, color="#64748B", lw=1.8):
    """PhotoImage de un icono suelto (en caché)."""
    clave = ("i", nombre, px, color, lw)
    if clave not in _cache:
        _cache[clave] = ImageTk.PhotoImage(pil_icono(nombre, px, color, lw))
    return _cache[clave]


def cuadro(nombre, lado=36, color="#2563EB", fondo="#E8F0FE", radio=9,
           px=18, lw=1.8, borde=None):
    """Icono centrado dentro de un cuadrado redondeado de color."""
    clave = ("c", nombre, lado, color, fondo, radio, px, lw, borde)
    if clave not in _cache:
        S = 4
        N = lado * S
        base = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(base)
        d.rounded_rectangle([0, 0, N - 1, N - 1], radius=radio * S,
                            fill=borde or fondo)
        if borde:
            d.rounded_rectangle([S, S, N - 1 - S, N - 1 - S],
                                radius=max(1, (radio - 1)) * S, fill=fondo)
        base = base.resize((lado, lado), Image.LANCZOS)
        ico = pil_icono(nombre, px, color, lw)
        o = (lado - px) // 2
        base.alpha_composite(ico, (o, o))
        _cache[clave] = ImageTk.PhotoImage(base)
    return _cache[clave]


def esquinas(r, fondo, borde=None):
    """4 esquinas redondeadas (arriba-izq, arriba-der, abajo-izq, abajo-der)."""
    clave = ("e", r, fondo, borde)
    if clave not in _cache:
        S = 6
        N = 2 * r * S
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, N - 1, N - 1], radius=r * S, fill=borde or fondo)
        if borde:
            d.rounded_rectangle([S, S, N - 1 - S, N - 1 - S],
                                radius=max(1, r - 1) * S, fill=fondo)
        im = im.resize((2 * r, 2 * r), Image.LANCZOS)
        trozos = (im.crop((0, 0, r, r)), im.crop((r, 0, 2 * r, r)),
                  im.crop((0, r, r, 2 * r)), im.crop((r, r, 2 * r, 2 * r)))
        _cache[clave] = [ImageTk.PhotoImage(t) for t in trozos]
    return _cache[clave]


def avatar(texto, px=44, fondo="#2B4A7A", color="#FFFFFF", tam=0.42):
    """Círculo de color con una letra o símbolo centrado (inicial, "?")."""
    clave = ("a", texto, px, fondo, color, tam)
    if clave not in _cache:
        S = 4
        N = px * S
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([0, 0, N - 1, N - 1], fill=fondo)
        d.text((N / 2, N / 2), texto, fill=color, font=_fuente(int(N * tam)),
               anchor="mm")
        _cache[clave] = ImageTk.PhotoImage(im.resize((px, px), Image.LANCZOS))
    return _cache[clave]


def foto_circular(ruta, px=44):
    """Foto de perfil recortada en círculo (PhotoImage; el que llama la guarda)."""
    S = 4
    N = px * S
    img = Image.open(ruta).convert("RGB")
    w, h = img.size
    lado = min(w, h)
    img = img.crop(((w - lado) // 2, (h - lado) // 2,
                    (w + lado) // 2, (h + lado) // 2)).resize((N, N), Image.LANCZOS)
    mascara = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mascara).ellipse([0, 0, N - 1, N - 1], fill=255)
    img = img.convert("RGBA")
    img.putalpha(mascara)
    return ImageTk.PhotoImage(img.resize((px, px), Image.LANCZOS))
