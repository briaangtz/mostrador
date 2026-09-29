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

| Producto               | Precio (ejemplo) | Tipo          |
| ---------------------- | ----------------: | ------------- |
| Garrafa 10 kg          |          $10.000 | gas           |
| Garrafa 15 kg          |          $15.000 | gas           |
| Garrafa ME             |          $16.000 | gas           |
| Garrafa 45 kg          |          $45.000 | gas           |
| Garrafa ECO PROPANO    |          $17.000 | gas           |
| Envase 10 kg           |           $8.000 | envase suelto |
| Envase 15 kg           |          $10.000 | envase suelto |
| Envase 45 kg           |          $20.000 | envase suelto |
| Envase ME              |          $11.000 | envase suelto |
| Envase ECO PROPANO     |          $12.000 | envase suelto |

Los precios se modifican libremente desde **Configuración → Productos y
precios** (también se pueden agregar o quitar productos).

**Dos familias que se tratan distinto en el Excel:**

* **Garrafas con gas** — las cinco garrafas. Van al recuadro **VENTA DE
  GARRAFAS** y su total nunca se mezcla con el de los envases.
* **Envases sueltos** — las cinco garrafas sin gas (que se devuelven o se
  venden aparte). Van al recuadro **VENTA DE ENVASES**, con un texto que
  aclara de qué son.

La clasificación es por nombre: todo producto que empieza con **"Envase"**
(envase nuevo incluido) entra en la segunda familia. *Garrafa 15ME* pasó a
llamarse **Garrafa ME** (el renombre se hace solo al abrir la base, sin tocar
ventas viejas).

En la pantalla **Inicio**, la lista *VENTAS POR PRODUCTO* muestra **únicamente
lo que se vendió** (los productos sin ventas no ocupan lugar) y cierra con una
fila **TOTAL GENERAL** con las unidades y la plata de todo el día.

## 2. Registro de ventas (pestaña "Ventas")

Cada venta se registra como un **TICKET**: primero se arman los productos y
después se carga cómo se pagó. Dos pasos:

**Paso 1 — los productos.** Se elige **Producto** (al elegirlo se carga su
precio automáticamente), **Cantidad** y **Precio unitario** (editable) y se
presiona **+ AGREGAR AL TICKET**. Se repite por cada producto que se lleve el
cliente (2 garrafas de 10, 1 de 45, 1 envase, etc.). Los productos van
apareciendo en la lista **PRODUCTOS DEL TICKET** con su subtotal, y con
**Quitar seleccionado** se saca alguno.

**Paso 2 — el pago.** Se elige el **Medio de pago** y, si hace falta, su
**Importe**, y se presiona **+ AGREGAR MEDIO DE PAGO**. Si pagó con dos medios
(por ejemplo $30.000 en efectivo y el resto por transferencia) se cargan los
dos. Los importes quedan en la lista **FORMAS DE PAGO**.

* Si no se carga ningún importe, el medio se completa solo con el total del
  ticket (el caso más común: todo en un solo medio).
* El **Nombre / Cliente** (primera fila) es opcional: se muestra en el
  listado, en el cierre y viaja al Excel.
* Debajo de las dos listas hay un aviso de cuadre: en rojo **"FALTAN $X …"**
  y en verde **"PAGOS = TOTAL"**. Si la suma de los medios no da exactamente
  el total, **no se puede registrar la venta**.
* Para **Transferencia** el **N° DE COMPROBANTE** es obligatorio dentro del
  mismo ticket (aunque el resto esté pago en efectivo).

Al presionar **REGISTRAR VENTA** el ticket queda guardado con: n° de ticket,
fecha y hora, usuario, productos con cantidades y precios, total, medios de
pago con sus importes, comprobante y nombre del cliente.

El sistema suma las unidades por producto y el dinero **por medio de pago sin
duplicar la venta**: una venta de $90.000 pagada con $30.000 en efectivo y
$60.000 transferidos cuenta como **una** operación, $30.000 en efectivo y
$60.000 en transferencias.

El **total** se calcula solo (`cantidad × precio unitario`) y el sistema
acumula la cantidad de garrafas vendidas durante el día, por producto y en
total. Ejemplo: 3 × Garrafa 10 kg a $10.000 = **$30.000**.

Los campos están repartidos en **dos filas** para que ninguno quede cortado ni
fuera de pantalla en monitores chicos.

Las ventas del día se listan en pantalla (con sus productos, sus formas de
pago y su comprobante). Si cargaste algo mal (por ejemplo 10 cuando son 9),
seleccionás **una o varias** ventas en la lista (Ctrl o Shift +
clic) y podés:

* **Editar venta seleccionada** — carga el ticket en el formulario con todos
  sus productos y sus medios de pago, corregís lo que haga falta y presionás
  **GUARDAR CAMBIOS** (no hace falta borrar).
* **Eliminar seleccionadas** — borra **todas las marcadas de una sola vez**,
  con una sola confirmación (no hace falta ir una por una).
* **Borrar toda la caja** — vacía por completo la caja del día (también con
  confirmación y contando cuántas ventas se eliminan).

Cada venta borrada queda registrada en el historial de actividad con su
usuario. Los tres botones solo funcionan mientras la caja esté abierta.

## 3. Medios de pago

* Efectivo
* Transferencia
* **Tarjetas** (agrupa los dos cobros con tarjeta):
  * Tarjeta de débito
  * Tarjeta de crédito

Los importes se mantienen separados en la base y se muestran **agrupados en
"TARJETAS" con su desglose** (débito / crédito) en la pantalla principal, en el
cierre, en el historial y en el Excel.

Un mismo ticket puede combinarse con **varios de ellos** (por ejemplo $30.000 en
efectivo + $60.000 transferidos): cada medio guarda su importe y, cuando es
transferencia, su N° de comprobante. El dinero se reparte entre los medios sin
que la venta se cuente dos veces.

## 4. Pantalla principal (pestaña "Inicio")

**CAJA DEL DÍA** muestra:

* Fecha actual
* Garrafas vendidas
* Total vendido
* Efectivo / Transferencias / **Tarjetas** (con detalle "Débito … • Crédito …")
* Total general
* Ventas por producto — **solo lo que se vendió** (los productos sin ventas
  no ocupan lugar), cada fila con su plata y sus **unidades**, y una fila
  final **TOTAL GENERAL** con la suma de todas las unidades y de todo el
  dinero del día.

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
* Garrafas vendidas por tipo (10 kg, 15 kg, ME, 45 kg, ECO PROPANO) y envases.
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
* Se pide **dentro del mismo ticket**, también cuando la transferencia es
  solo una parte del pago (por ejemplo $30.000 en efectivo y el resto
  transferido).
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
secciones, contado una sola vez, y debajo **Cantidad de operaciones** con los
**tickets únicos** (no las filas). La columna **Nombre** es el cliente cargado
en la venta (puede quedar vacía).

**Una fila por cobro, con su ticket.** Cada venta aparece en la sección de
cada medio de pago que la cubrió, con el importe que le tocó y el n° de ticket
delante (por ejemplo `#12 · María López`). Una venta de $90.000 pagada con
$30.000 en efectivo y $60.000 transferidos ocupa **dos filas** ($30.000 en
DINERO EN EFECTIVO y $60.000 en TRANSFERENCIAS) y **nunca** suma $90.000 dos
veces. La carga completa y el N° de comprobante viajan en cada fila.

Para las transferencias ya no hace falta una exportación aparte: todo lo del
período sale junto, separado por secciones.

### Dos recuadros arriba de la hoja

Antes del detalle, la hoja **Movimientos** arranca con el título **RESUMEN DE
VENTAS POR SECCIÓN DE PAGO** y **dos recuadros compactos** para responder de
un vistazo cuántas unidades y cuánta plata salieron con cada medio de pago.

**Cómo se reparte un ticket pagado con varios medios:**

* Las **unidades** van al **medio principal** de la venta (el que aporta más
  dinero; si empata, el primero que se cargó). Así las unidades de los
  recuadros coinciden con las unidades realmente vendidas.
* El **dinero** de cada fila se reparte **por familia de producto** (garrafas
  con gas / envases sueltos), proporcional a los subtotales de esa venta. Por
  ejemplo, si garrafas valen $60.000 y un envase $20.000 de un ticket pagado
  con $30.000 en efectivo, a garrafas le tocan $22.500 y al envase $7.500.
* Por eso los dos recuadros **suman el dinero cobrado exacto** y los
  controles marcan **COINCIDE**: ni se duplica ni se pierde plata.
* Los **controles de unidades** y **de dinero** (uno por recuadro) comparan
  las filas del recuadro con el detalle de cobros que sigue abajo.

**Recuadro 1 — VENTA DE GARRAFAS (con gas)** (una columna por producto,
**solo los que se vendieron** en el período, con sus siglas: 10KG, 15KG, 45KG,
ME, ECO; aclaración: *"Solo figuran las garrafas que se vendieron en el
período"*):

| Sección         | 10KG | 15KG | Unidades | Total $ |
| --------------- | ---- | ---- | -------- | ------- |
| EFEC            | 2    | 1    | 3        | $35.000 |
| TARJETA         | 0    | 2    | 2        | $30.000 |
| TRANS           | 1    | 0    | 1        | $15.000 |
| **TOTAL GENERAL** | 3  | 3    | **6**    | **$80.000** |

| Control            | Qué muestra                                              |
| ------------------ | -------------------------------------------------------- |
| CONTROL DE UNIDADES | `EFEC(3) + TARJETA(2) + TRANS(1) = 6` → **COINCIDE**      |
| CONTROL DE DINERO   | `EFEC($35.000) + TARJETA($30.000) + TRANS($15.000) = $80.000` → **COINCIDE** |

* Las filas son **EFEC**, **TARJETA** y **TRANS**; la que cierra el cuadro es
  **TOTAL GENERAL** (EFEC + TARJETA + TRANS, contado una sola vez por
  producto).
* Los dos controles comparan lo de arriba con el detalle de movimientos que
  sigue abajo y marcan **COINCIDE** o **REVISAR**: así un descuadre salta a la
  vista antes de imprimir.
* Cada recuadro tiene la misma estructura; lo único que cambian son las
  columnas: **una por producto que se vendió**, en el orden 10 → 15 → 45 →
  ME → ECO.
* Si no hubo ventas en el período aparece una sola fila: *Sin ventas en el
  período.*

**Recuadro 2 — VENTA DE ENVASES** (igual, pero solo con los **envases
sueltos** que se vendieron). Su aclaración dice qué son: *"Envases sueltos,
sin gas: se venden y se devuelven aparte de las garrafas (10 kg, 15 kg, 45 kg,
ME y ECO PROPANO). Nunca se suman con las garrafas con gas."* No aparece si no
se vendió ningún envase. Así los envases nunca se mezclan con las garrafas
con gas.

El detalle de movimientos que sigue abajo no cambia: columnas **Nombre | Carga
| N° Comprobante / Tarjeta | Total** (cada campo ocupa dos columnas) y el
**TOTAL GENERAL** en la última fila.

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

## 20. Soporte del sistema (ayuda 24/7)

En el lateral, arriba al lado del logo, hay un botón azul **?** siempre
visible. Abre una **ventana flotante de chat** encima de la pantalla que
estés usando (sin bloquearla: seguís trabajando mientras preguntás).

Funciona **sin internet y sin costo**: no llama a ningún servicio externo.
Es un buscador sobre la documentación real del programa (`ayuda.py`), así
que responde con lo que el sistema efectivamente hace y **nunca inventa**.

* **Preguntas rápidas** en la parte superior: abrir/cerrar caja, registrar
  una venta, exportar a Excel, crear usuario y respaldados.
* O escribís tu pregunta abajo (**Enter** o el botón *Preguntar*).
* Cada respuesta indica de dónde sale: *Fuente: sección 5 del manual*.
* Si la pregunta es muy vaga (por ejemplo «caja») en vez de inventar
  ofrece los temas que pueden servirte. Si no hay nada cargado, lo dice
  y sugiere otras palabras.
* El **✕** oculta la ventana sin perder la conversación; al volver a
  tocar **?** sigue todo lo conversado.

Cubre: apertura y cierre de caja, arqueo y diferencia, reapertura de
cajas, ventas y comprobantes, medios de pago y tarjetas, Excel e
impresión A4, rendición por buzón y calculadora de billetes, historial y
estadísticas, usuarios y permisos, Mi cuenta y fotos, respaldos,
productos y precios, nuevo día, errores frecuentes, trazabilidad,
instalación y qué hace el programa.

---

## 21. Rendición por buzón (planilla + calculadora de billetes)

Botón **Rendición** en el lateral (permiso `rendicion`). La pantalla tiene
**dos pestañas**, las dos siempre a la vista:

### Pestaña 1 — CARGA / RENDICIÓN

Se carga una sola vez todo lo que muestra la planilla:

| Sector | Campos |
| ------ | ------ |
| Cabecera | FECHA · CHOFER |
| Detalle | TIPO · CANTIDAD · IMPORTE · TOTAL (filas con **+ AGREGAR**) |
| Secciones | GASTOS · CAJA · ENVÍOS · TARJETAS · TRANSFERENCIAS · RECIBOS |
| Efectivo | TOTAL DE BILLETES (viene de la pestaña 2, no se escribe) |
| Cheques | CLIENTE · N.º DE CHEQUE · BANCO · IMPORTE |
| Pies | OBSERVACIONES |

* **TARJETAS** y **TRANSFERENCIAS** se **precargan con las ventas del día**
  y se corrigen a mano cuando haga falta; **PRECARGAR DEL DÍA** las vuelve
  a traer y **LIMPIAR TODO** arranca de cero.
* **GUARDAR RENDICIÓN** guarda por día: hay **un solo registro por fecha**
  (se actualiza, nunca se duplica) y al volver a entrar sigue todo cargado.

### Pestaña 2 — CALCULADORA DE BILLETES

Filas **BILLETE | CANTIDAD | IMPORTE** con las denominaciones
$100, $200, $500, $1.000, $2.000, $10.000 y $20.000: cada fila calcula
`Cantidad × valor` en vivo y al pie cierra el **TOTAL EFECTIVO**.

**El enlace es automático**: ese total aparece solo en el campo
**EFECTIVO** de la pestaña 1 y en la planilla impresa. Si cambiás un
billete, cambian los dos. Así nunca se carga la misma cifra dos veces ni
quedan números distintos.

### Planilla A4

**GENERAR PLANILLA A4** guarda lo cargado (y lo exporta) en un `.xlsx`
con la estructura del formulario original: título, cabecera, detalle,
secciones, chequeos, conteo de billetes y observaciones, con los totales
calculados. La hoja queda configurada para **imprimir en UNA sola hoja
A4 vertical** (`fitToWidth = fitToHeight = 1`, sin cuadrícula y con área
de impresión definida), en tipografía grande y con los casilleros sin
cargar en blanco.

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
| `excel.py`            | Excel por secciones (A4 horizontal) y planilla de rendición (A4 vertical) |
| `ui_cierre.py`        | Ventana de cierre, arqueo y autenticación      |
| `ui_historial.py`     | Historial y detalle de cierres, reapertura      |
| `ui_rendicion.py`     | Rendición por buzón: carga + calculadora de billetes |
| `ui_config.py`        | Precios, fondo, respaldos y contraseña propia   |
| `ui_cuenta.py`        | Mi cuenta: foto de perfil, datos y contraseña   |
| `ayuda.py`            | Base de conocimiento y buscador del soporte     |
| `ui_ayuda.py`         | Ventana flotante de soporte (chat de ayuda)     |
| `estilos.py`, `util.py` | Estilos y formatos de moneda/fechas          |
| `icono.ico`           | Ícono del programa                             |
| `crear_icono.py`      | Regenera `icono.ico` desde una imagen          |
| `garrafas.db`         | Base de datos con todos los datos (respaldar)  |
| `test_sistema.py`     | Pruebas automáticas (`python test_sistema.py`) |
| `Iniciar.bat`         | Acceso directo para abrir el programa          |
| `Compilar MOSTRADOR.bat` | Regenera el `.exe` con un doble clic         |
| `dist\MOSTRADOR.exe`  | Programa compilado para llevar a otra PC       |
