# -*- coding: utf-8 -*-
"""Lee las mitigaciones de seguridad del header PE (DllCharacteristics)
sin dependencias: ASLR/DEP/CET/CFG + firma Authenticode.

Uso:  python tools/pe_check.py dist\\MOSTRADOR.exe dist\\Actualizador.exe

Lo usa CI (seguridad.yml) para exigir ASLR + DEP en los ejecutables que
se publican. Sale con código 1 si falta ALGUNA mitigación obligatoria,
así el pipeline se corta antes de publicar.
"""
import struct
import sys

FLAGS = [
    (0x0020, "HIGH_ENTROPY_VA (ASLR 64-bit)"),
    (0x0040, "DYNAMIC_BASE (ASLR)"),
    (0x0100, "NX_COMPAT (DEP)"),
    (0x0400, "GUARD_CF (Control Flow Guard)"),
    (0x4000, "APPCONTAINER"),
    (0x8000, "NO_SEH (sin manejadores SEH en el binario)"),
]

# Obligatorias para publicar (ver auditoría AppSec, hallazgo #6)
OBLIGATORIAS = (0x0020 | 0x0040, 0x0100)   # ASLR (alta entropía o DYNAMIC_BASE) y DEP


def leer_pe(ruta):
    """Devuelve un dict con el análisis del PE, o None si no es PE."""
    with open(ruta, "rb") as f:
        datos = f.read()
    if len(datos) < 0x40:
        return None
    e_lfanew = struct.unpack_from("<I", datos, 0x3C)[0]
    if datos[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        return None
    magic = struct.unpack_from("<H", datos, e_lfanew + 24)[0]
    opc = e_lfanew + 24
    dllchars = struct.unpack_from("<H", datos, opc + 70)[0]
    ndir = struct.unpack_from("<I", datos, opc + 108)[0]
    dd = opc + 112
    tam_firma = 0
    if ndir > 4 and len(datos) >= dd + 40:
        tam_firma = struct.unpack_from("<I", datos, dd + 4 * 8)[0]
    return {
        "ruta": ruta,
        "pe": "PE32+ (64-bit)" if magic == 0x20B else "PE32 (32-bit)",
        "dllchars": dllchars,
        "flags": {nombre: bool(dllchars & bit) for bit, nombre in FLAGS},
        "firma": bool(tam_firma),
    }


def main(rutas):
    fallos = 0
    for ruta in rutas:
        info = leer_pe(ruta)
        if info is None:
            print(f"{ruta} -> no es PE")
            fallos += 1
            continue
        print(f"\n{ruta}")
        print(f"  formato: {info['pe']}  |  "
              f"DllCharacteristics: 0x{info['dllchars']:04X}")
        for _bit, nombre in FLAGS:
            ok = info["flags"][nombre]
            marca = "SÍ" if ok else "NO"
            print(f"  [{marca}] {nombre}")
        print(f"  [{'SÍ' if info['firma'] else 'NO'}] Firma Authenticode presente")
        # Exigencias mínimas: ASLR (cualquiera de sus dos bits) y DEP
        aslr = info["flags"]["HIGH_ENTROPY_VA (ASLR 64-bit)"] or \
            info["flags"]["DYNAMIC_BASE (ASLR)"]
        dep = info["flags"]["NX_COMPAT (DEP)"]
        if not (aslr and dep):
            print("  ERROR: faltan mitigaciones obligatorias (ASLR y/o DEP)")
            fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print("Uso: python tools/pe_check.py <ejecutable.exe> [...]")
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
