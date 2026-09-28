# Control de Ventas de Garrafas — Caja Diaria

Programa de escritorio (Python + Tkinter) para llevar el control diario de las
ventas de garrafas y realizar automáticamente el **control y cierre de caja** al
finalizar cada jornada.

## Cómo iniciar

**Doble clic en `Iniciar.bat`**

o desde una terminal:

```
python main.py
```

No requiere instalar nada adicional para los datos (usa SQLite, incluido en
Python). Las dos librerías de apoyo se instalan con:

```
python -m pip install -r requirements.txt
```

(openpyxl para el Excel y Pillow para la foto de perfil; en el `.exe` ya vienen
incluidas). Los datos se guardan en el archivo `garrafas.db`, en la misma carpeta
del programa (hacé copia de seguridad de ese archivo para respaldar todo).

## Inicio de sesión

Al abrir el programa aparece la pantalla de **Usuario** y **Contraseña**: sin
iniciar sesión no se puede usar ninguna función (ni registrar ventas ni abrir ni
cerrar cajas).

* Primer usuario: **admin** / **admin** (rango DESARROLLADOR).
* Cambiá esa contraseña al instalar, desde *Configuración → Mi cuenta* o desde
  el panel **Mi cuenta**.
* Las contraseñas se guardan **cifradas con sal** (nunca en texto plano) y no se
  muestran en el sistema.
* Los intentos fallidos de ingreso quedan registrados.
* Para salir de una cuenta: botón **Cerrar sesión** (lateral izquierdo, abajo).

---

## 1. Productos

Al abrir el programa ya están cargados:

| Producto      | Precio (ejemplo) |
| ------------- | ----------------: |
| Garrafa 10 kg |          $10.000 |
| Garrafa 15 kg |          $15.000 |
| Garrafa 15ME  |          $16.000 |
| Garrafa 45 kg |          $45.000 |

Los precios se modifican libremente desde **Configuración → Productos y
precios** (también se pueden agregar o quitar productos).

## 2. Registro de ventas (pestaña "Ventas")

Para cada venta se selecciona:

* **Producto** (al elegirlo se carga su precio automáticamente)
* **Cantidad**
* **Precio unitario** (editable)
* **Nombre / Cliente** (opcional; se muestra en el listado y viaja al Excel)
* **Medio de pago**

El **total** se calcula solo (`cantidad × precio unitario`) y el sistema
acumula la cantidad de garrafas vendidas durante el día, por producto y en
total. Ejemplo: 3 × Garrafa 10 kg a $10.000 = **$30.000**.

Los campos están repartidos en **dos filas** para que ninguno quede cortado ni
fuera de pantalla en monitores chicos.

Las ventas del día se listan en pantalla. Si cargaste algo mal (por ejemplo 10
cuando son 9), seleccionás la venta en la lista y podés:

* **Editar venta seleccionada** — carga la venta en el formulario, corregís la
  cantidad o el precio y presionás **GUARDAR CAMBIOS** (no hace falta borrar).
* **Eliminar venta seleccionada** — la quita y recalcula los totales del día.

Ambos botones solo funcionan mientras la caja esté abierta.

## 3. Medios de pago

* Efectivo
* Transferencia
* **Tarjetas** (agrupa los dos cobros con tarjeta):
  * Tarjeta de débito
  * Tarjeta de crédito

Los importes se mantienen separados en la base y se muestran **agrupados en
"TARJETAS" con su desglose** (débito / crédito) en la pantalla principal, en el
cierre, en el historial y en el Excel.

## 4. Pantalla principal (pestaña "Inicio")

**CAJA DEL DÍA** muestra:

* Fecha actual
* Garrafas vendidas
* Total vendido
* Efectivo / Transferencias / **Tarjetas** (con detalle "Débito … • Crédito …")
* Total general
* Ventas por producto

Y dos botones, cada uno con el **usuario responsable**:

* **ABRIR CAJA — (usuario)** — registra la apertura: usuario, fecha, hora y
  **monto inicial** (fondo con el que empezás el día). Se pide una sola vez por
  día; hasta abrir la caja **no se pueden cargar ventas**. El monto que pongas
  ahí es el que usa el cierre como *efectivo esperado*.
* **CERRAR CAJA — (usuario)** — abre el arqueo y el cierre (sección 5).

Si la caja todavía no fue abierta, la pantalla avisa: *"Sin apertura registrada
— presioná ABRIR CAJA…"*.

## 5. Cierre de caja

Al presionar *CERRAR CAJA* se abre una ventana con:

1. **RESUMEN DEL DÍA** — garrafas vendidas de cada producto, total de
   garrafas y total de ventas.
2. **MEDIOS DE PAGO** — efectivo esperado, transferencias, **Tarjetas** con su
   discriminación (*· Tarjeta de débito* y *· Tarjeta de crédito*) y total
   general cobrado.
3. **ARQUEO DE CAJA** — conteo físico de billetes:

   | Billete | Cantidad | Subtotal          |
   | ------: | -------: | ----------------: |
   | $20.000 |       20 |           $400.000 |
   | $10.000 |       10 |           $100.000 |
   | $2.000  |        5 |            $10.000 |
   | $1.000  |        5 |             $5.000 |
   | $500    |        2 |             $1.000 |
   | **TOTAL** |      | **$516.000** |

   Denominaciones: $100, $200, $500, $1.000, $2.000, $10.000 y $20.000.
4. **COMPARACIÓN DE CAJA**

   * Efectivo esperado: $520.000
   * Efectivo contado: $516.000
   * Diferencia = contado − esperado = **−$4.000** → **FALTANTE**
   * Si da positivo: **SOBRANTE**; si da cero: **CAJA CUADRADA**

5. Botón **CONFIRMAR CIERRE**, que guarda: fecha, hora de cierre, total de
   garrafas, total vendido, efectivo esperado, efectivo contado,
   transferencias, débito, crédito, total general, diferencia y estado.

Al confirmar, **la ventana de cierre se cierra por completo** (no abre otra
ventana ni otra pestaña), el cierre **queda registrado** en la base y en el
registro de actividad, y el programa **vuelve solo a la pantalla Inicio** ya
con la caja cerrada. Si la caja del día está **sin ventas**, el cierre se hace
**en un clic** (sin arqueo ni contraseña).

> El **efectivo esperado** = ventas en efectivo del día + fondo inicial
> registrado al abrir la caja (si la caja no tiene apertura, se usa el fondo
> inicial de *Configuración → Caja*, por defecto $0).

## 6. Caja bloqueada y reapertura

Una vez confirmado, la caja queda **cerrada y bloqueada**: no permite agregar ni
borrar ventas ni volver a cerrarla.

Si hay que modificar algo, se usa **Historial de cierres → Reabrir caja
(contraseña)**. Es una función **exclusiva del rango DESARROLLADOR**: pide la
contraseña del usuario que tiene la sesión abierta. Guardada cifrada, nunca en
texto plano.

## 7. Nuevo día

Al abrir el programa en una fecha nueva (o si cruza la medianoche con el
programa abierto) se **crea automáticamente una nueva caja diaria**, con los
contadores en cero y separada del día anterior.

Si alguna caja anterior quedó sin cerrar, aparece un aviso en la pantalla
principal y un indicador en el lateral.

> **Cajas de otro día**: desde el combo *Ver caja de la fecha* de Inicio se
> puede seleccionar cualquier caja para consultarla o cerrarla. Si elegiste una
> fecha a mano, el programa **no te devuelve a la caja de hoy** aunque pase la
> medianoche: solo salta automáticamente si no seleccionaste ninguna.

## 8. Historial de cierres

Pestaña **Historial de cierres**: tabla con Fecha, Total vendido, Efectivo,
Transferencia, **Tarjetas** (débito + crédito), Diferencia y Estado (cuadrada /
sobrante / faltante). Con doble clic o con *Ver detalle* se abre el cierre
completo de ese día: totales (incluido *Total tarjetas* con su discriminación
*· Tarjeta de débito* y *· Tarjeta de crédito*), arqueo de billetes y ventas
registradas.

---

## 9. Estadísticas (pestaña "Estadísticas")

Sección independiente para consultar la información registrada, con **filtros
por fecha** (día específico o rango personalizado) y atajos rápidos: **Hoy**,
**Últimos 7 días**, **Este mes** y **Todo**.

Se visualiza:

* Total de ventas realizadas y venta promedio.
* Garrafas vendidas por tipo (10 kg, 15 kg, 15ME, 45 kg).
* Total de dinero recaudado.
* Total cobrado en efectivo, transferencia y **Tarjetas**, con el desglose
  "Débito … • Crédito …" debajo de la tarjeta.
* Cantidad de transferencias realizadas.
* Evolución de las ventas por día (gráfico de barras por fecha).
* Resumen de los cierres de caja del período (fecha, total, medios de pago,
  diferencia y estado).

## 10. Transferencias con comprobante obligatorio

Al registrar una venta con medio de pago **Transferencia**, el campo **N° DE
COMPROBANTE** se marca en rojo como **OBLIGATORIO**:

* Sin número de comprobante **no se puede guardar la venta**: aparece el aviso
  *"Para registrar una venta paga con TRANSFERENCIA es obligatorio ingresar el
  N° de comprobante"*.
* El número queda asociado a esa venta, se muestra en el listado de ventas y se
  conserva en el historial y en el detalle de los cierres.

En los demás medios de pago el campo es opcional.

## 11. Exportación de movimientos a Excel (imprimible en A4)

Botón **EXPORTAR A EXCEL** (dentro de Estadísticas). Permite elegir el archivo
y el **rango de fechas** (del día, de la semana, del mes o personalizado) con
los filtros de arriba.

El archivo `.xlsx` queda **preparado para imprimir directo en A4 horizontal**
(sin tocar nada: orientación horizontal, tamaño A4, ajuste al ancho de una
página, títulos repetidos en cada página, área de impresión y márgenes
configurados, y la fila de encabezados congelada en pantalla).

El contenido se organiza en **tres secciones**, cada una con su subtotal y con
las columnas **Nombre | Carga | N° Comprobante / Tarjeta | Total**. La sección
**TARJETAS** agrupa los dos cobros con tarjeta y los **discrimina en dos
bloques**, cada uno con su propio subtotal:

| Sección          | Contenido                                            |
| ---------------- | ---------------------------------------------------- |
| TRANSFERENCIAS   | ventas pagadas con transferencia (N° de comprobante) |
| **TARJETAS**     | bloque **TARJETA DE DÉBITO** y bloque **TARJETA DE CRÉDITO** (N° de tarjeta) |
| DINERO EN EFECTIVO | ventas en efectivo (sin comprobante)               |

Dentro de TARJETAS cada bloque cierra con su *Total Tarjeta de débito* /
*Total Tarjeta de crédito*, y la sección cierra con **TOTAL TARJETAS** (la suma
de los dos bloques). Al final figura el **TOTAL GENERAL** de todas las
secciones, contado una sola vez. La columna **Nombre** es el cliente cargado en
la venta (puede quedar vacía).

Para las transferencias ya no hace falta una exportación aparte: todo lo del
período sale junto, separado por secciones.

## 12. Transferencias en el cierre de caja

El cierre diario separa claramente efectivo, transferencias y **tarjetas**
(con débito y crédito discriminados), y
para las transferencias muestra:

* el **monto total**,
* la **cantidad de transferencias realizadas**, y
* una tabla con el **detalle de cada comprobante** (N°, hora, producto,
  cantidad e importe).

Ese mismo detalle queda guardado en el cierre y se puede ver después desde
**Historial de cierres → Ver detalle**.

---

## 13. Rangos y niveles de acceso

El sistema trabaja con dos rangos (definidos en `permisos.py` y ampliables sin
tocar el resto del código):

### DESARROLLADOR

Mayor nivel de acceso. Puede:

* Crear, modificar, activar/desactivar y eliminar usuarios; asignar rangos y
  contraseñas.
* Configurar precios de productos, fondo inicial y parámetros generales.
* Acceder a Estadísticas y a la exportación a Excel.
* Reabrir cajas cerradas (con contraseña).
* Consultar historial, cierres y el registro de actividad.

### USUARIO

Permisos limitados para el personal de caja:

* Iniciar sesión con su usuario y contraseña.
* Registrar ventas (efectivo, transferencia, débito y crédito).
* Realizar el arqueo y **cerrar la caja**.
* Consultar la información de su turno y el historial de cierres.

**No** puede: crear ni eliminar usuarios, cambiar rangos, modificar precios o
configuración general, ver Estadísticas, exportar a Excel ni reabrir cajas.

Los permisos se validan **dos veces**: el botón de la sección no aparece para el
usuario sin permiso y, además, el sistema lo valida internamente aunque se
intente entrar por otro medio.

### Permisos individuales por usuario

Además de los permisos del rango, **cada usuario puede tener sus propios
permisos**:

* En **Administración**, al crear o modificar un usuario aparece el marco
  **PERMISOS DE ESTE USUARIO**, con casillas agrupadas (CAJAS, VENTAS Y
  COBROS, SECCIONES, REPORTES Y PERFIL).
* Si el administrador **marca casillas**, ese usuario pasa a usar exactamente
  esas marcadas (ni más ni menos), sin importar su rango.
* Si **no marca ninguna**, el usuario sigue usando los permisos por defecto de
  su rango (así se comportan todos los usuarios existentes hasta que se le
  asigne algo).
* **DESARROLLADOR**: siempre tiene todos los permisos, no se le pueden sacar.
* Dentro de VENTAS Y COBROS hay un permiso por **medio de pago**
  (efectivo/transferencia/débito/crédito): el combo de la venta solo ofrece
  los medios permitidos y un cobro con medio no permitido se rechaza.

## 14. Panel de Administración (solo DESARROLLADOR)

Nueva entrada en el menú lateral: **Administración → Usuarios y actividad**.
Permite:

* **Crear usuarios** (con botones *Generar usuario* y *Generar contraseña*).
* **Modificar** nombre, rango y estado del usuario.
* **Asignar permisos individuales** (casillas por permiso; vacío = usa los del
  rango).
* **Cambiar contraseñas** (se muestran solo al crearlas/cambiarlas, para poder
  pasárselas al usuario).
* **Activar / Desactivar** usuarios (un usuario desactivado no puede ingresar).
* **Eliminar** usuarios (con protecciones: no se puede borrarte a vos mismo ni
  al último DESARROLLADOR activo).
* **Ver permisos** de cada rango, detallados.
* **Registro de actividad**: qué hizo cada usuario y cuándo.

Reglas de seguridad: no se puede eliminar al último DESARROLLADOR, no se puede
desactivar la propia sesión y no se permiten nombres de usuario duplicados.

## 15. Apertura y cierre de caja con responsable

* **Apertura (manual)**: con el botón **ABRIR CAJA — (usuario)** de la pantalla
  Inicio se registra **usuario, fecha, hora y monto inicial**. Requiere tener la
  sesión iniciada (nunca se puede abrir caja sin sesión). La caja nace *sin
  abrir*: hasta registrar la apertura no se pueden cargar ventas. Se muestra
  como *"Abierta por … a las …"*.
* **Cierre**: antes de CONFIRMAR CIERRE el sistema pide **la contraseña del
  usuario conectado**. El cierre guarda: usuario responsable, fecha, hora, total
  de efectivo, transferencias, tarjetas, total general, diferencia, cantidad de
  operaciones, cantidad de transferencias y **número de comprobantes**.

## 16. Control y trazabilidad (registro de actividad)

Todas las operaciones importantes quedan asociadas al usuario que las realizó:

* **Registro de actividad** (dentro de Administración): fecha, hora, usuario,
  acción y detalle de cada evento — inicio de sesión (y rechazados), ventas
  registradas / modificadas / eliminadas, aperturas, cierres, reaperturas,
  altas y bajas de usuarios, cambios de contraseña y exportaciones a Excel.
* El listado de **Ventas** muestra la columna **"Registró"** con el usuario de
  cada venta.
* El **detalle del cierre** indica quién abrió y quién cerró la caja.

De esta forma se responde siempre a: *¿quién ingresó → quién abrió la caja → qué
operaciones hizo → quién cerró la caja → cuándo → con qué resultado?*

## 17. Respaldo automático de la base de datos

Los respaldos se guardan solos en la carpeta **`respaldos/`** (junto al
programa), con nombre `garrafas_aaaa-mm-dd_hh-mm-ss.db`:

* **Al abrir el programa** — uno por día (si ese día ya hay respaldo, no duplica).
* **Al cerrar el programa** — si ese día todavía no hay respaldo.
* **En cada cierre de caja** — instantánea en el momento crítico.
* Se conservan los **últimos 60 respaldos**; los más viejos se borran solos.
* Opción para **activar/desactivar** el respaldo automático en
  *Configuración → Respaldo de la base de datos*.
* Todo queda registrado en el registro de actividad.

En *Configuración → Respaldo de la base de datos* también hay:

* **Respaldar ahora** — genera un respaldo manual al instante.
* **Abrir carpeta de respaldos** — abre `respaldos/` en el explorador.
* **Restaurar respaldo…** — elige un archivo `.db` de la carpeta, hace primero
  un respaldo de seguridad de la base actual y la reemplaza (reiniciar el
  programa después).

> **Copia de seguridad extra:** además de `respaldos/`, seguí haciendo una copia
> de `garrafas.db` a un pendrive o nube de vez en cuando. Para eso alcanza con
> copiar el archivo (y la carpeta `respaldos/` si querés el histórico).

---

## 18. Mi cuenta (foto, datos y contraseña)

El botón **Mi cuenta** (último de la navegación, visible para todos los rangos)
muestra:

* **Foto de perfil** — botón *Elegir imagen…* para tomar una imagen
  **del Escritorio** (JPG, PNG, BMP o ICO) con vista previa; se guarda en la
  carpeta `perfiles/`, junto a la base, recortada en cuadrado y reducida.
  El botón *Quitar foto* la elimina. Si hay foto, también se ve **en el
  lateral**, al lado de tu usuario; sin foto se muestra un avatar genérico.
  **Cada usuario tiene su propia foto**: la tuya no se pisa con la de nadie
  más (se guarda en un archivo por usuario).
* **Tus datos** — usuario, rango, último acceso y fecha de creación.
* **Cambiar mi contraseña** — pide la contraseña actual, la nueva y su
  repetición (mínimo 4 caracteres). También sigue disponible en
  *Configuración*.
* **Cerrar sesión** — igual que el botón del lateral.

---

## 19. Diseño adaptable a cualquier pantalla

La ventana y todos los paneles se adaptan al tamaño del monitor:

* La ventana se ajusta al **95 % de la pantalla** (con tope y tamaño mínimo),
  siempre centrada y **sin superponerse** con otras ventanas.
* Los paneles largos (Ventas, Estadísticas, Configuración, Historial,
  Administración) tienen **scroll con la rueda del mouse**: si no entra todo,
  se desplaza en vez de cortarse.
* Ningún campo, botón ni texto queda **fuera de pantalla, cortado u oculto**:
  el formulario de ventas está en dos filas y los textos largos se acomodan
  solos.
* Los diálogos (cierre de caja y detalle) también se adaptan al tamaño de la
  pantalla y tienen scroll interno.

---

## Ícono del programa

El ícono es `icono.ico` (garrafa YPF GAS sobre tarjeta blanca con fondo azul de
la marca). Para regenerarlo o usar otra imagen:

1. Cambiá la imagen/ruta en `crear_icono.py`.
2. Ejecutá `python crear_icono.py`.
3. Reiniciá el programa.

En el código se aplica solo si `icono.ico` existe (si no, se abre con el ícono
por defecto de Windows).

## Llevarlo a otra PC

### Opción A — Archivo `.exe` (la más cómoda)

Se generó **`dist\MOSTRADOR.exe`**. En la otra PC **no hace falta tener
Python**: se copia únicamente ese archivo y se ejecuta. Los datos se guardan en
`garrafas.db`, junto al `.exe`.

Para regenerarlo (por ejemplo, después de cambiar algo en el código), **doble
clic en `Compilar MOSTRADOR.bat`**, o bien manualmente:

```
python -m PyInstaller --noconfirm --onefile --windowed --name MOSTRADOR --icon "icono.ico" --add-data "icono.ico;." main.py
```

> Si querés llevar los datos ya cargados, copiá también `garrafas.db` (y la
> carpeta `respaldos/`, si querés el histórico) junto al `.exe`. Si la otra PC
> empieza de cero, basta con el `.exe`.

### Opción B — Copiar la carpeta

Se copia la carpeta completa a la otra PC, que debe tener **Python 3** desde
[python.org](https://www.python.org/downloads/) (viene con Tkinter incluido) y
se abre con `Iniciar.bat` o `python main.py`.

---

## Archivos del proyecto

| Archivo               | Función                                        |
| --------------------- | ---------------------------------------------- |
| `main.py`             | Ventana principal, navegación, login e ícono   |
| `permisos.py`         | Rangos y permisos del sistema                  |
| `database.py`         | Base de datos (SQLite): usuarios, cajas, ventas, cierres, actividad |
| `ui_login.py`         | Pantalla de inicio de sesión                   |
| `ui_admin.py`         | Panel de Administración: usuarios y actividad  |
| `ui_inicio.py`        | Pantalla "Caja del día"                        |
| `ui_ventas.py`        | Registro, edición y borrado de ventas, comprobante |
| `ui_estadisticas.py`  | Estadísticas con filtros y evolución diaria   |
| `excel.py`            | Excel por secciones (A4 horizontal) a imprimir  |
| `ui_cierre.py`        | Ventana de cierre, arqueo y autenticación      |
| `ui_historial.py`     | Historial y detalle de cierres, reapertura      |
| `ui_config.py`        | Precios, fondo, respaldos y contraseña propia   |
| `ui_cuenta.py`        | Mi cuenta: foto de perfil, datos y contraseña   |
| `estilos.py`, `util.py` | Estilos y formatos de moneda/fechas          |
| `icono.ico`           | Ícono del programa                             |
| `crear_icono.py`      | Regenera `icono.ico` desde una imagen          |
| `garrafas.db`         | Base de datos con todos los datos (respaldar)  |
| `test_sistema.py`     | Pruebas automáticas (`python test_sistema.py`) |
| `Iniciar.bat`         | Acceso directo para abrir el programa          |
| `Compilar MOSTRADOR.bat` | Regenera el `.exe` con un doble clic         |
| `dist\MOSTRADOR.exe`  | Programa compilado para llevar a otra PC       |
