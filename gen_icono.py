# -*- coding: utf-8 -*-
"""
Genera icono.ico para el MOSTRADOR: cuadrado redondeado con degradado azul
y una garrafa de gas sólida en blanco. Multi-resolución (16..256).
"""
import math
from PIL import Image, ImageDraw

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradiente_w(size, c_sup, c_inf, radio):
    """Cuadrado redondeado con degradado vertical + sutil brillo superior."""
    S = 4
    N = size * S
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = radio * S
    # mascara de esquinas redondeadas
    mask = Image.new("L", (N, N), 0)
    dm = ImageDraw.Draw(mask)
    dm.rounded_rectangle([0, 0, N - 1, N - 1], radius=r, fill=255)
    # degradado vertical
    grad = Image.new("RGBA", (N, N))
    dg = ImageDraw.Draw(grad)
    for y in range(N):
        t = y / (N - 1)
        col = lerp(c_sup, c_inf, t)
        dg.line([(0, y), (N, y)], fill=col + (255,))
    img.paste(grad, (0, 0), mask)
    # brillo suave arriba (elipse blanca tenue)
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    dg2 = ImageDraw.Draw(glow)
    dg2.ellipse([-N * 0.2, -N * 0.55, N * 1.2, N * 0.45],
                fill=(255, 255, 255, 46))
    glow.putalpha(Image.composite(glow.split()[3], Image.new("L", (N, N), 0), mask))
    img = Image.alpha_composite(img, glow)
    return img

def dibujar_garrafa(d, N, color):
    """Garrafa de gas sólida (silueta clara) centrada en lienzo N."""
    u = N / 256.0

    def X(v): return v * u

    # ---- cuerpo (domo superior + lados rectos + base) ----
    bx0, bx1 = 80, 176          # ancho del cuerpo
    by_top, by_bot = 92, 210    # alto del cuerpo
    # cuerpo como rect redondeado grande
    d.rounded_rectangle([X(bx0), X(by_top), X(bx1), X(by_bot)],
                        radius=X(26), fill=color)
    # aplanar un poco el fondo (base apoyada)
    d.rectangle([X(bx0), X(by_bot - 24), X(bx1), X(by_bot)], fill=color)
    d.rounded_rectangle([X(bx0), X(by_bot - 20), X(bx1), X(by_bot + 4)],
                        radius=X(10), fill=color)

    # ---- banda horizontal (etiqueta) ----
    banda = (37, 99, 235)  # azul acento
    d.rectangle([X(bx0), X(140), X(bx1), X(166)], fill=banda)

    # ---- collarín / protección de válvula (arco superior) ----
    cx = (bx0 + bx1) / 2
    # dos postes
    d.rounded_rectangle([X(cx - 30), X(58), X(cx - 18), X(96)],
                        radius=X(5), fill=color)
    d.rounded_rectangle([X(cx + 18), X(58), X(cx + 30), X(96)],
                        radius=X(5), fill=color)
    # anillo superior (manija)
    d.rounded_rectangle([X(cx - 34), X(46), X(cx + 34), X(60)],
                        radius=X(7), fill=color)
    # válvula pequeña al centro
    d.rounded_rectangle([X(cx - 9), X(70), X(cx + 9), X(94)],
                        radius=X(4), fill=color)

def generar_icono(size=256):
    c_sup = (43, 120, 240)    # azul claro arriba
    c_inf = (21, 60, 150)     # azul oscuro abajo
    img = gradiente_w(size, c_sup, c_inf, radio=int(size * 0.22))
    S = 4
    N = size * S
    overlay = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    dibujar_garrafa(d, N, (255, 255, 255, 255))
    img = Image.alpha_composite(img, overlay)
    return img.resize((size, size), Image.LANCZOS)

if __name__ == "__main__":
    tamaños = [16, 24, 32, 48, 64, 128, 256]
    imgs = [generar_icono(s) for s in tamaños]
    imgs[-1].save("icono.ico", sizes=[(s, s) for s in tamaños])
    # previsualizacion png grande
    generar_icono(256).save("icono_preview.png")
    print("icono.ico generado con tamaños:", tamaños)
