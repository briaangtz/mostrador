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
| `database.py` | Columnas `modulo` y `token_venta` en `ventas`; tablas `auditoria` y `precios_usuario`; config `MODULO_USUARIO_ACTIVO`; funciones `log_auditoria`, `get_precio_usuario`, `set_precio_usuario`, `get_precios_usuario`, `borrar_precio_usuario`; `registrar_ticket` acepta `modulo`/`token_venta` y valida contra la lista de precios USUARIO |
| `main.py` | Import de `VentasUsuarioPanel`, entrada NAV, panel en `self.paneles`, `_actualizar_nav` y `mostrar` respetan interruptor |
| `ui_ventas_usuario.py` | NUEVO: panel de ventas USUARIO (nombre/apellido, productos, pagos múltiples). El precio sale de la tabla `precios_usuario` y aparece BLOQUEADO (etiqueta solo lectura); si el producto no tiene precio en la lista, la venta se bloquea |
| `ui_config.py` | Columna «Precio USUARIO» en la lista de productos, campo y botón «Guardar precio USUARIO» (solo DESARROLLADOR); si el campo se deja vacío, el producto se quita de la lista USUARIO (su venta queda bloqueada) |
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
- La tabla `precios_usuario` queda en la base pero sin efecto (nadie la consulta).
- Las ventas de MOSTRADOR no se ven afectadas.

## Sobre el precio bloqueado (agregado posterior)

- El precio del módulo USUARIO se carga SOLO desde **Configuración → Productos y precios → «Guardar precio USUARIO»** (solo DESARROLLADOR), en la tabla `precios_usuario` (centavos, entero).
- En la venta, el precio es una etiqueta de solo lectura: no hay campo editable que se pueda tipear.
- Doble control: además de la UI bloqueada, `registrar_ticket` rechaza en el backend cualquier venta `USUARIO` cuyo precio no coincida exactamente con la lista (o si el producto no está en la lista).
- Cada cambio de precio queda en `auditoria` (solo inserción).
- Para desbloquear un producto hay que asignarle precio; para sacarlo de la lista USUARIO, dejar el campo vacío al guardar.
