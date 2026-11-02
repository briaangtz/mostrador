# REVERTIR_ESTE_CAMBIO.md — Cómo deshacer el ajuste de Ventas USUARIO

Este documento explica cómo volver atrás el ajuste de "Ventas USUARIO"
(sin clientes registrados, pagos múltiples) aplicado en la rama
`ajuste/ventas-usuario-sin-clientes`.

## Puntos seguros

| Tag / Commit | Qué representa |
|---|---|
| `v0-original-antes-de-modulos` | Sistema original v1.3.6 sin cambios |
| `HEAD` de `ajuste/ventas-usuario-sin-clientes` | Con el ajuste aplicado |

## Archivos modificados

| Archivo | Qué cambió |
|---|---|
| `database.py` | Columnas `modulo` y `token_venta` en `ventas`; tabla `auditoria`; config `MODULO_USUARIO_ACTIVO`; función `log_auditoria`; `registrar_ticket` acepta `modulo` y `token_venta` |
| `main.py` | Import de `VentasUsuarioPanel`, entrada NAV, panel en `self.paneles`, `_actualizar_nav` y `mostrar` respetan interruptor |
| `ui_ventas_usuario.py` | NUEVO: panel de ventas USUARIO (nombre/apellido, productos, pagos múltiples) |
| `REVERTIR_ESTE_CAMBIO.md` | Este archivo |

## Cómo revertir completamente

Desde la carpeta del proyecto, en la rama `ajuste/ventas-usuario-sin-clientes`:

```bash
# 1. Volver al commit original (deshace todos los cambios de código)
git checkout v0-original-antes-de-modulos -- .

# 2. Eliminar el archivo nuevo
rm ui_ventas_usuario.py

# 3. Confirmar el reverso
git add -A
git commit -m "Revertir ajuste Ventas USUARIO (vuelve a v1.3.6 original)"
```

## Cómo revertir solo la base de datos

La base de datos real está en `%LOCALAPPDATA%\Garrafas\garrafas.db`. 
Se hizo un backup antes del cambio en:

```
C:\Users\doble\Documents\Proyecto mostrador\BACKUPS\ajuste_ventas_usuario_20261102_094703\garrafas_20261102_094703.db
SHA-256: B60662BA6B1C59673379FE06EEAA0CC01745112F97AC5775F66C67D4A95ECAE6
```

Para restaurar (con el programa CERRADO):

```bash
copy "C:\Users\doble\Documents\Proyecto mostrador\BACKUPS\ajuste_ventas_usuario_20261102_094703\garrafas_20261102_094703.db" garrafas.db
```

## Qué sucede con los datos si se revierte

- Las ventas registradas con `modulo='USUARIO'` quedan en la tabla `ventas` pero el panel ya no existirá. Se pueden consultar directamente desde SQL.
- La tabla `auditoria` queda vacía de registros de este ajuste.
- Las ventas de MOSTRADOR no se ven afectadas.
