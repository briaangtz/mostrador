# REVERTIR_ESTE_CAMBIO.md — Cómo deshacer el ajuste de Ventas USUARIO

Este documento explica cómo volver atrás el ajuste de "Ventas USUARIO"
(sin clientes registrados, pagos múltiples) aplicado en la rama
`ajuste/ventas-usuario-sin-clientes`.

## Puntos seguros

| Tag / Commit | Qué representa |
|---|---|
| `v0-original-antes-de-modulos` | Sistema original v1.3.6 sin cambios |
| `HEAD` de `ajuste/ventas-usuario-sin-clientes` | Con el ajuste aplicado (Ventas U.C: USUARIO + COMERCIO, USUARIO precio bloqueado desde Configuración, COMERCIO precio editable a mano, estadísticas por módulo) |
| `etapa-4-precios-modulo-usuario-comercio-ok` | Precios por módulo: USUARIO bloqueado desde Configuración; COMERCIO precio editable a mano en la venta |
| `etapa-5-estadisticas-por-modulo-ok` | Estadísticas individuales por módulo (USUARIO, MOSTRADOR, COMERCIO) + GENERAL consolidada con exportación Excel |
| `etapa-6-exportar-excel-selector-modulo-ok` | Exportar a Excel con selector VENTAS / USUARIO / COMERCIO; filtro por módulo en exportar_movimientos |

## Archivos modificados

| Archivo | Qué cambió |
|---|---|
| `database.py` | Columnas `modulo` y `token_venta` en `ventas`; tablas `auditoria`, `precios_usuario` y `precios_comercio`; config `MODULO_USUARIO_ACTIVO`; funciones `log_auditoria`, `get_precio_usuario`, `set_precio_usuario`, `get_precios_usuario`, `borrar_precio_usuario`, `get_precio_comercio`, `set_precio_comercio`, `get_precios_comercio`, `borrar_precio_comercio`; `registrar_ticket` acepta `modulo`/`token_venta` y valida precio contra lista USUARIO (venta bloqueada si no hay precio); COMERCIO permite precio a mano (no valida contra lista); `estadisticas()` incluye `por_modulo` con desglose individual por módulo y clave `general` consolidada |
| `main.py` | Import de `VentasUCFrame`, entrada NAV «Ventas U.C» (cubre USUARIO y COMERCIO), panel en `self.paneles`, `guardar_venta_uc` con `modulo` y `token_venta` |
| `ventas_uc.py` | NUEVO: panel combinado Ventas U.C (toggle USUARIO/COMERCIO), productos y precios leídos de DB según el módulo. USUARIO: precio bloqueado (solo lectura, venta bloqueada si no hay precio). COMERCIO: precio editable a mano en la venta (varía por categoría de comercio), filas habilitadas incluso sin precio asignado; pagos múltiples con total/pagado/saldo, comprobante obligatorio en transferencia |
| `ui_ventas_usuario.py` | NUEVO (etapa previa): panel de ventas USUARIO (nombre/apellido, productos, pagos múltiples). El precio sale de la tabla `precios_usuario` y aparece BLOQUEADO (etiqueta solo lectura); si el producto no tiene precio en la lista, la venta se bloquea |
| `ui_config.py` | Columna «Precio USUARIO» y «Precio COMERCIO» en la lista de productos, campos y botones «Guardar precio USUARIO» / «Guardar precio COMERCIO» (solo DESARROLLADOR); si el campo se deja vacío, el producto se quita de la lista correspondiente (su venta queda bloqueada) |
| `ui_estadisticas.py` | Sección de estadísticas por módulo (4 tarjetas: USUARIO, MOSTRADOR, COMERCIO, GENERAL) y selector Combobox (VENTAS / USUARIO / COMERCIO) junto al botón «EXPORTAR A EXCEL» |
| `excel.py` | `exportar_movimientos(desde, hasta, destino, modulo=None)` acepta filtro opcional por módulo; se elimina `exportar_por_modulo()` |
| `REVERTIR_ESTE_CAMBIO.md` | Este archivo |

## Cómo revertir completamente

Desde la carpeta del proyecto, en la rama `ajuste/ventas-usuario-sin-clientes`:

```bash
# 1. Volver al commit original (deshace todos los cambios de código)
git checkout v0-original-antes-de-modulos -- .

# 2. Eliminar los archivos nuevos
rm ui_ventas_usuario.py ventas_uc.py

# 3. Confirmar el reverso
git add -A
git commit -m "Revertir ajuste Ventas U.C (vuelve a v1.3.6 original)"
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

- Las ventas registradas con `modulo='USUARIO'` o `modulo='COMERCIO'` quedan en la tabla `ventas` pero el panel ya no existirá. Se pueden consultar directamente desde SQL.
- La tabla `auditoria` queda vacía de registros de este ajuste.
- Las tablas `precios_usuario` y `precios_comercio` quedan en la base pero sin efecto (nadie las consulta).
- Las ventas de MOSTRADOR no se ven afectadas.

## Sobre el precio bloqueado (agregado posterior)

- El precio del módulo USUARIO se carga SOLO desde **Configuración → Productos y precios → «Guardar precio USUARIO»** (solo DESARROLLADOR), en la tabla `precios_usuario` (centavos, entero).
- En la venta, el precio es una etiqueta de solo lectura: no hay campo editable que se pueda tipear.
- Doble control: además de la UI bloqueada, `registrar_ticket` rechaza en el backend cualquier venta `USUARIO` cuyo precio no coincida exactamente con la lista (o si el producto no está en la lista).
- Cada cambio de precio queda en `auditoria` (solo inserción).
- Para desbloquear un producto hay que asignarle precio; para sacarlo de la lista USUARIO, dejar el campo vacío al guardar.

## Sobre el precio del módulo COMERCIO (editable a mano en la venta)

- El precio del módulo COMERCIO **se escribe a mano en la venta** (no está bloqueado). Esto permite variar el precio según la categoría de cada comercio sin tener que crear una entrada de precio por cada uno en Configuración.
- En la venta U.C con módulo COMERCIO, aparece un campo de precio editable donde se puede tipear el importe unitario.
- `registrar_ticket` **no valida** el precio para COMERCIO: acepta cualquier importe unitario cargado en la venta.
- La tabla `precios_comercio` sigue existiendo en la base por si se quiere usar como referencia, pero no afecta a las ventas de COMERCIO.
- Cada cambio de precio en COMERCIO **no queda registrado en auditoría** (solo se registra la venta completa con su precio unitario).

## Sobre las estadísticas por módulo y exportación a Excel

- `estadisticas()` devuelve una clave `por_modulo` con desglose individual para USUARIO, MOSTRADOR y COMERCIO, más una clave `general` que consolida todos los módulos (efectivo, tarjetas, transferencias, garrafas, total vendido, cantidad de ventas).
- Cada módulo muestra: cantidad de ventas, garrafas, total vendido, efectivo, tarjetas (débito + crédito) y transferencias.
- Desde la pestaña Estadísticas se puede exportar a Excel con el botón «EXPORTAR A EXCEL» y un selector Combobox con tres opciones: VENTAS (todo), USUARIO o COMERCIO. Se exporta solo lo seleccionado del período cargado.
