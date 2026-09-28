# -*- coding: utf-8 -*-
"""
Genera icono.ico a partir de la imagen del escritorio
'descuento DOBLE G_page-0001.jpg' (recorta la garrafa YPF GAS).

Uso:  python crear_icono.py
"""
import os

from PIL import Image, ImageDraw

FUENTE = r"C:\Users\doble\Desktop\descuento DOBLE G_page-0001.jpg"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icono.ico")
PREVIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_previa_icono.png")

# Región de la garrafa dentro de la imagen original
CORTE = (1470, 1390, 2090, 2490)
TAMANIOS = [16, 32, 48, 64, 128, 256]


def construir_icono():
    original = Image.open(FUENTE)
    garrafa = original.crop(CORTE)

    # Recorta los bordes sobrantes por color claro (opaco, sin transparencias)
    gris = garrafa.convert("L")
    mascara = gris.point(lambda v: 255 if v < 235 else 0)
    bbox = mascara.getbbox()
    if bbox:
        # Amplía un poco para no cortar los bordes claros de la garrafa
        x0, y0, x1, y1 = bbox
        margen = 18
        garrafa = garrafa.crop((max(0, x0 - margen), max(0, y0 - margen),
                                min(garrafa.width, x1 + margen),
                                min(garrafa.height, y1 + margen)))

    # Color de fondo tomado de la franja azul del afiche (marca)
    azul = original.getpixel((200, 2700))
    print("Color de marca:", azul)

    # Color claro del fondo de la foto, para que la tarjeta no se vea costurada
    esquinas = [garrafa.getpixel(p) for p in
                [(2, 2), (garrafa.width - 3, 2),
                 (2, garrafa.height - 3), (garrafa.width - 3, garrafa.height - 3)]]
    claro = tuple(sum(c[i] for c in esquinas) // 4 for i in range(3))
    print("Color de la tarjeta:", claro)

    # 1) Tarjeta blanca redondeada
    tam = 232
    margen = (256 - tam) // 2
    tarjeta = Image.new("RGBA", (tam, tam), claro + (255,))

    # 2) Garrafa dentro de la tarjeta (sin recortar, con margen)
    disponible = tam - 24
    escala = min(disponible / garrafa.width, disponible / garrafa.height)
    nuevo = garrafa.resize((max(1, int(garrafa.width * escala)),
                            max(1, int(garrafa.height * escala))), Image.LANCZOS)
    tarjeta.paste(nuevo.convert("RGB"),
                  ((tam - nuevo.width) // 2, (tam - nuevo.height) // 2))

    # 3) Esquinas redondeadas
    radio = 44
    borde = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(borde).rounded_rectangle([0, 0, tam - 1, tam - 1],
                                            radius=radio, fill=255)
    tarjeta.putalpha(borde)

    # 4) Fondo de marca + tarjeta encima
    lienzo = Image.new("RGBA", (256, 256), azul + (255,))
    lienzo.alpha_composite(tarjeta, (margen, margen))

    lienzo.save(PREVIA, "PNG")
    lienzo.save(SALIDA, format="ICO", sizes=[(s, s) for s in TAMANIOS])
    print("Generado:", SALIDA)
    print("Previa:", PREVIA)


if __name__ == "__main__":
    construir_icono()
