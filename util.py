# -*- coding: utf-8 -*-
"""Utilidades de formato numérico y fechas."""

import os
import sys

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def money(valor):
    """Formatea como moneda: $10.000 / $516.500,50"""
    if valor is None:
        valor = 0
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    signo = "-" if valor < 0 else ""
    valor = abs(valor)

    if abs(valor - round(valor)) < 1e-9:
        entero = int(round(valor))
        return signo + "$" + f"{entero:,}".replace(",", ".")
    dec = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return signo + "$" + dec


def parse_numero(texto):
    """Convierte '10.000' o '10000,50' o '$ 10.000' a número. Devuelve None si no es válido."""
    if texto is None:
        return None
    t = str(texto).strip().replace("$", "").replace(" ", "")
    if t == "":
        return None
    # Quitar separador de miles (.) y usar coma decimal ->
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    elif "." in t:
        # Si el punto está seguido de exactamente 3 dígitos, se asume miles
        partes = t.split(".")
        if len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
            t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def parse_entero(texto):
    n = parse_numero(texto)
    if n is None:
        return None
    return int(round(n))


def fecha_larga(iso):
    """'2026-09-10' -> 'jueves 10 de septiembre de 2026'"""
    if not iso:
        return ""
    try:
        a, m, d = [int(x) for x in iso.split("-")]
    except ValueError:
        return iso
    import datetime
    dia_semana = DIAS[datetime.date(a, m, d).weekday()]
    return f"{dia_semana} {d} de {MESES[m - 1]} de {a}"


def fecha_corta(iso):
    if not iso:
        return ""
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def fecha_a_iso(texto):
    """Convierte '10/09/2026', '10-09-2026' o '2026-09-10' a ISO (YYYY-MM-DD).

    Devuelve None si el texto no es una fecha válida."""
    if texto is None:
        return None
    t = str(texto).strip().replace("-", "/")
    if not t:
        return None
    partes = t.split("/")
    try:
        if len(partes) == 3 and len(partes[0]) <= 2:      # dd/mm/aaaa
            d, m, a = (int(x) for x in partes)
        elif len(partes) == 3 and len(partes[0]) == 4:    # aaaa/mm/dd
            a, m, d = (int(x) for x in partes)
        else:
            return None
        from datetime import date as _date
        return _date(a, m, d).isoformat()
    except (ValueError, TypeError):
        return None


def ruta_recurso(nombre):
    """Ruta de un archivo auxiliar (icono.ico), tanto en código como en .exe."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, nombre)


def carpeta_datos():
    """Carpeta FIJA donde viven los datos del programa (portabilidad).

    Con PyInstaller --onefile, todo lo que se escriba junto al .exe es
    frágil: el .exe puede estar en una carpeta de solo lectura, en un
    pendrive o puede ser reemplazado por el actualizador. Por eso la
    base de datos, los respaldos, las fotos de perfil y los logs van
    a %LOCALAPPDATA%\\Garrafas, que siempre existe y siempre es del
    usuario.

    Se crea sola la primera vez. Funciona igual con ``python main.py``
    o con el .exe compilado.
    """
    raiz = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    ruta = os.path.join(raiz, "Garrafas")
    os.makedirs(ruta, exist_ok=True)
    return ruta
