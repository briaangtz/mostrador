# -*- coding: utf-8 -*-
"""
Soporte del sistema: base de conocimiento local + buscador.

Responde preguntas sobre CÓMO USAR el programa usando la documentación
misma del sistema. Es 100 % offline: no llama a ningún servicio externo,
no cuesta nada por consulta y no inventa respuestas fuera de la base.

Uso:
    import ayuda
    r = ayuda.resolver("¿Cómo cierro la caja?")
    r["ok"]        -> True si encontró un tema
    r["tema"]      -> el tema (titulo, parrafos, seccion, ejemplos)
    r["ambiguas"]  -> temas empatados (si la pregunta es vaga)
"""

import difflib
import re
import unicodedata

# Puntaje mínimo para considerar que se respondió la pregunta
UMBRAL = 3

# Palabras que no aportan (se descartan de la pregunta y de las claves)
_STOP = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "u", "a", "en", "con", "sin", "sobre", "por", "para", "que",
    "se", "me", "te", "le", "les", "lo", "mi", "tu", "sus", "es", "son",
    "ser", "esta", "estan", "hay", "como", "cuando", "donde", "cual",
    "cuales", "quien", "quienes", "favor", "gracias", "hola", "buenos",
    "buenas", "dia", "dias", "tarde", "noche", "puedo", "quiero", "debo",
    "necesito", "esto", "ese", "esa", "este", "mas", "muy", "ya", "tambien",
    "hago", "hacer", "puede", "podes", "the", "para", "asi", "pues", "cual",
    "todo", "todos", "toda", "todas", "otro", "otra", "otros", "otras",
}


# --------------------------------------------------------------- utilidades
def normalizar(texto):
    """Minúsculas, sin acentos, sin signos: 'Cierre' -> 'cierre'."""
    txt = unicodedata.normalize("NFD", str(texto))
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def tokens(texto):
    """Palabras con significado de un texto (sin acentos ni relleno)."""
    return [t for t in normalizar(texto).split()
            if t not in _STOP and len(t) >= 3]


def _parecido(palabra, claves):
    """True si la palabra coincide con alguna clave (typos y conjugaciones)."""
    if len(palabra) < 4:
        return False
    for c in claves:
        if len(c) < 4:
            continue
        if abs(len(c) - len(palabra)) <= 3:
            if difflib.SequenceMatcher(None, palabra, c).ratio() >= 0.80:
                return True
        # por prefijo: "transf" -> "transferencia"
        if c.startswith(palabra[:4]) or palabra.startswith(c[:4]):
            return True
    return False


# ------------------------------------------------------------- base de datos
# Cada tema: id, titulo, claves (palabras sueltas), frases (enteras),
# parrafos (la respuesta), seccion (de dónde sale) y ejemplos (sugerencias).
TEMAS = [
    dict(
        id="abrir_caja",
        titulo="Abrir la caja del día",
        claves="abrir abro apertura apertura abierta fondo inicial monto "
               "inicial empezar turno dia caja",
        frases=["abrir la caja", "abrir caja", "apertura de caja",
                "fondo inicial", "monto inicial", "como abro"],
        parrafos=[
            "Entrá a la pantalla **Inicio** y presioná **ABRIR CAJA — (tu "
            "usuario)**. Te pide el **monto inicial**: es el fondo con el "
            "que empezás el día, la plata que dejás en la caja antes de "
            "vender.",
            "El sistema guarda quién abrió, la fecha y la hora. Se pide "
            "**una sola vez por día** y, hasta que no la abras, **no se "
            "pueden cargar ventas**.",
            "Ese monto inicial es el que el cierre usa después como "
            "*efectivo esperado*.",
        ],
        seccion="secciones 4 y 15 del manual",
        ejemplos=["¿Cómo abro la caja del día?",
                  "¿Qué es el fondo inicial?"],
    ),
    dict(
        id="cerrar_caja",
        titulo="Cerrar la caja y hacer el arqueo",
        claves="cerrar cierro cierre cerrada cerrado arqueo billetes "
               "faltante sobrante sobro sobra cuadrada diferencia contado "
               "esperado confirmar confirmacion vacia un clic estado",
        frases=["cerrar la caja", "cerrar caja", "cierre de caja",
                "arqueo de caja", "hacer el arqueo", "caja cuadrada",
                "caja sin ventas", "cerrar sin ventas", "cierre en un clic",
                "que significa faltante", "que significa sobrante"],
        parrafos=[
            "Desde la pantalla **Inicio** apretá **CERRAR CAJA — (tu "
            "usuario)** y se abre el arqueo, con el resumen del día y los "
            "medios de pago.",
            "En **ARQUEO DE CAJA** contás los billetes (de $100 a $20.000). "
            "El sistema calcula el efectivo contado y lo compara con el "
            "esperado: **diferencia = contado − esperado**. Si da menos es "
            "**FALTANTE**, si da más es **SOBRANTE** y si da cero es "
            "**CAJA CUADRADA**.",
            "Después apretás **CONFIRMAR CIERRE**. La ventana se cierra "
            "sola, el cierre queda en el historial y en el registro de "
            "actividad, y el programa vuelve a la pantalla **Inicio** con "
            "la caja cerrada.",
            "Si la caja está **sin ventas**, el cierre sale en **un clic**: "
            "no pide arqueo ni contraseña.",
        ],
        seccion="secciones 5 y 15 del manual",
        ejemplos=["¿Cómo cierro la caja?",
                  "¿Qué significa FALTANTE o SOBRANTE?"],
    ),
    dict(
        id="reabrir_caja",
        titulo="Reabrir una caja cerrada (bloqueada)",
        claves="reabrir reabro reabrir bloqueada bloqueado desbloquear "
               "cerrada por error corregir cierre contraseña developer "
               "desarrollador historial",
        frases=["reabrir caja", "reabrir la caja", "caja bloqueada",
                "volver a abrir", "corregir el cierre", "caja cerrada"],
        parrafos=[
            "Una vez confirmada, la caja queda **cerrada y bloqueada**: no "
            "deja agregar ni borrar ventas ni volver a cerrarla.",
            "Para corregir algo andá a **Historial de cierres** y apretá "
            "**Reabrir caja (contraseña)**. Es una función **exclusiva del "
            "rango DESARROLLADOR** y pide la contraseña de tu usuario. Al "
            "reabrirla vuelve a quedar abierta.",
            "Nunca se puede borrar el arqueo de una caja que ya tiene "
            "ventas: la vía correcta es reabrirla y corregir desde ahí.",
        ],
        seccion="sección 6 del manual",
        ejemplos=["La caja quedó cerrada por error, ¿cómo la reabro?"],
    ),
    dict(
        id="ventas",
        titulo="Registrar, editar o eliminar una venta",
        claves="venta ventas vender registrar carga cargar producto "
               "cantidad precio unitario cliente nombre total editar "
               "modificar corregir eliminar borrar formulario guardar "
               "listado varias masiva vaciar seleccion ticket tickets "
               "agregar productos medios importe faltan cuadre suman",
        frases=["registrar una venta", "cargar una venta", "como se vende",
                "editar venta", "eliminar venta", "borrar venta",
                "corregir una venta", "borrar todas las ventas",
                "vaciar la caja", "eliminar varias ventas",
                "agregar al ticket", "registrar un ticket"],
        parrafos=[
            "En la pantalla **Ventas** cada venta es un **TICKET** con dos "
            "pasos. **Paso 1:** elegís **Producto** (carga su precio solo), "
            "**Cantidad** y **Precio unitario**, y apretás **+ AGREGAR AL "
            "TICKET**. Repetís por cada producto que se lleve el cliente.",
            "**Paso 2:** elegís el **Medio de pago** y su **Importe** y "
            "apretás **+ AGREGAR MEDIO DE PAGO**. Si el ticket se paga con "
            "dos medios (por ejemplo efectivo + transferencia) cargás los "
            "dos. Si no cargás ningún importe, ese medio se completa solo "
            "con el total del ticket.",
            "Abajo de las dos listas se ve el cuadre: en rojo **FALTAN $X** "
            "cuando los medios no suman exactamente el total (y **no deja "
            "registrar**) y en verde **PAGOS = TOTAL** cuando cierra. Si "
            "algún medio es Transferencia, el **N° de comprobante** es "
            "obligatorio. Recién con todo cerrado apretás **REGISTRAR "
            "VENTA** y la venta queda guardada con su ticket, productos, "
            "medios, importes y comprobante.",
            "Las ventas del día se listan abajo. Para corregir algo, "
            "seleccioná la venta y apretá **Editar venta seleccionada**: se "
            "carga el ticket con todos sus productos y sus medios de pago, "
            "arreglás y apretás **GUARDAR CAMBIOS**.",
            "**Para borrar en masa** (no hace falta ir una por una): con "
            "Ctrl o Shift + clic marcás **varias ventas** a la vez y apretás "
            "**Eliminar seleccionadas** — se borran todas juntas con una "
            "sola confirmación. Y si querés empezar de cero, **Borrar toda "
            "la caja** vacía por completo el día (también te pregunta "
            "antes).",
            "Los tres botones solo funcionan mientras la caja esté "
            "**abierta**, y cada venta borrada queda registrada en el "
            "registro de actividad con tu usuario.",
        ],
        seccion="sección 2 del manual",
        ejemplos=["¿Cómo registro una venta?",
                  "Cargué mal la cantidad, ¿cómo la corrijo?"],
    ),
    dict(
        id="pantalla_inicio",
        titulo="Pantalla Inicio: lo vendido y el TOTAL GENERAL",
        claves="inicio pantalla resumen unidades total general vendidas "
               "vendido producto productos lista barras tarjetas efectivo "
               "transferencias dia",
        frases=["pantalla inicio", "que muestra el inicio", "total general",
                "cuantas unidades vendi", "ventas por producto"],
        parrafos=[
            "La pantalla **Inicio** muestra la **CAJA DEL DÍA**: fecha, "
            "unidades vendidas, total vendido, lo cobrado en efectivo, "
            "transferencias y tarjetas, y quién abrió la caja con cuánto "
            "monto inicial.",
            "Debajo, **VENTAS POR PRODUCTO** lista **únicamente lo que se "
            "vendió**: los productos sin ventas no ocupan lugar ni se "
            "muestran.",
            "Cada fila trae el dinero y las **unidades** de ese producto y, "
            "al final, hay una fila **TOTAL GENERAL** con la suma de "
            "**todas las unidades** y de **todo el dinero** del día. "
            "Ejemplo: si vendiste 2 en efectivo, 2 en tarjeta y 6 en "
            "transferencia, el TOTAL GENERAL dice **10 unidades**.",
        ],
        seccion="sección 4 del manual",
        ejemplos=["¿Qué muestra la pantalla Inicio?",
                  "¿Qué es el TOTAL GENERAL?"],
    ),
    dict(
        id="medios_pago",
        titulo="Medios de pago: efectivo, transferencia y tarjetas",
        claves="medio medios pago pagos efectivo transferencia tarjeta "
               "tarjetas debito credito cobro cobrar agrupa desglose combo "
               "como cobro",
        frases=["medio de pago", "medios de pago", "tarjeta de debito",
                "tarjeta de credito", "cobrar con tarjeta"],
        parrafos=[
            "Hay tres grupos: **Efectivo**, **Transferencia** y "
            "**Tarjetas**. Tarjetas agrupa los dos cobros con tarjeta y "
            "muestra el detalle *Débito … • Crédito …* en la pantalla "
            "principal, en el cierre, en el historial y en el Excel.",
            "Los importes se guardan por separado en la base (débito y "
            "crédito), así que el desglose siempre está disponible aunque "
            "se muestre agrupado.",
            "**Un ticket puede pagarse con varios medios**: cargás el "
            "primero con su importe y apretás **+ AGREGAR MEDIO DE PAGO**; "
            "después el segundo (o tercero). Los importes tienen que sumar "
            "exactamente el total: si faltan o sobran, el aviso en rojo "
            "dice cuánto falta y **no deja registrar**. El dinero queda "
            "repartido por medio **sin que la venta se cuente dos veces**.",
            "El combo de la venta solo ofrece los medios que tu usuario "
            "**tiene permiso** para cobrar: si elegís uno no permitido, el "
            "sistema rechaza la venta.",
        ],
        seccion="sección 3 del manual",
        ejemplos=["¿Cómo se muestran las tarjetas?",
                  "¿Qué medios de pago hay?"],
    ),
    dict(
        id="transferencia",
        titulo="Transferencias y N° de comprobante",
        claves="transferencia transferencias comprobante numero comprobantes "
               "n obligatorio banco cbu alias no me deja guardar",
        frases=["numero de comprobante", "n de comprobante",
                "comprobante obligatorio", "venta con transferencia",
                "me pide comprobante"],
        parrafos=[
            "Cuando el medio de pago es **Transferencia**, el campo **N° DE "
            "COMPROBANTE** es **obligatorio**: se marca en rojo y sin ese "
            "número no se puede guardar la venta.",
            "Se pide **dentro del mismo ticket**, también cuando la "
            "transferencia es solo una parte del pago (por ejemplo $30.000 "
            "en efectivo y el resto transferido).",
            "En los demás medios de pago ese campo es opcional.",
            "El número queda en la venta, en el listado, en el historial, "
            "en el detalle del cierre y en el Excel. El cierre también "
            "muestra el detalle de cada comprobante (N°, hora, producto, "
            "cantidad e importe).",
        ],
        seccion="secciones 10 y 12 del manual",
        ejemplos=["No me deja guardar una transferencia",
                  "¿Dónde veo los comprobantes?"],
    ),
    dict(
        id="excel",
        titulo="Exportar a Excel e imprimir",
        claves="excel exportar exportacion archivo xlsx hoja imprimir "
               "impresion a4 horizontal planilla descargar movimiento "
               "movimientos secciones general resumen unidades envases "
               "control efectivo tarjeta transferencia recuadro recuadros "
               "columnas vendidos",
        frases=["exportar a excel", "bajar el excel", "imprimir el excel",
                "excel a4", "hoja de calculo", "resumen de unidades",
                "cuántas garrafas salieron", "resumen de ventas"],
        parrafos=[
            "En **Estadísticas** apretá **EXPORTAR A EXCEL**, elegí el "
            "archivo y el rango de fechas (con los filtros de arriba).",
            "El archivo sale listo para **imprimir en A4 horizontal** sin "
            "tocar nada: orientación horizontal, tamaño A4, ajuste al ancho "
            "de una página, títulos repetidos en cada página, área de "
            "impresión y encabezado congelado.",
            "Arriba de todo sale el título **RESUMEN DE VENTAS POR SECCIÓN "
            "DE PAGO** y **dos recuadros**. El primero, **VENTA DE GARRAFAS "
            "(con gas)**, tiene **una columna por producto que se vendió** "
            "(con sus siglas 10KG, 15KG, 45KG, ME y ECO, en ese orden; las "
            "que no se vendieron no aparecen) y las filas **EFEC**, "
            "**TARJETA** y **TRANS**, que cierran con su **TOTAL GENERAL**.",
            "El segundo recuadro, **VENTA DE ENVASES**, es igual pero solo "
            "con los **envases sueltos**, con un texto que aclara qué son "
            "y que nunca se suman con las garrafas con gas. Si no se vendió "
            "ningún envase, ese recuadro no aparece.",
            "Debajo de cada recuadro hay dos filas de **CONTROL DE "
            "UNIDADES** y **CONTROL DE DINERO**, con la cuenta "
            "EFEC(...) + TARJETA(...) + TRANS(...) = total. Si dice "
            "**COINCIDE** el cuadre está bien; si dice **REVISAR**, hay que "
            "revisar antes de imprimir. Si una venta se pagó con dos medios, "
            "las **unidades** van al medio que aporta más dinero y el "
            "**dinero** se reparte entre garrafas y envases proporcional a "
            "esa venta: así los dos recuadros suman exacto.",
            "Después sigue el detalle en tres secciones — "
            "**TRANSFERENCIAS**, **TARJETAS** (bloque "
            "TARJETA DE DÉBITO y bloque TARJETA DE CRÉDITO, cada uno con su "
            "subtotal, y el **TOTAL TARJETAS**) y **DINERO EN EFECTIVO** — "
            "con las columnas Nombre | Carga | N° Comprobante / Tarjeta | "
            "Total, y al final el **TOTAL GENERAL** contado una sola vez.",
        ],
        seccion="sección 11 del manual",
        ejemplos=["¿Cómo exporto a Excel?",
                  "¿Cómo imprimo el reporte en A4?"],
    ),
    dict(
        id="rendicion",
        titulo="Planilla de rendición por buzón y calculadora de billetes",
        claves="rendicion rendir buzón buzon planilla rendiciones carga "
               "calculadora billete billetes conteo arqueo efectivo cheques "
               "cheque gastos emision emisión cobro tarjetas transferencias "
               "chofer observaciones secciones seccion detalle importe "
               "cantidad total imprimir a4 guardar",
        frases=["planilla de rendicion", "rendicion por buzon",
                "cargar la rendicion", "calculadora de billetes",
                "cuanto efectivo tengo", "conteo de billetes",
                "imprimir la planilla"],
        parrafos=[
            "**Rendición** (botón en el lateral) abre **dos pestañas**: "
            "**1 · CARGA / RENDICIÓN** y **2 · CALCULADORA DE BILLETES**.",
            "En la pestaña 1 se carga la planilla completa: **FECHA** y "
            "**CHOFER**, el **DETALLE** con sus columnas Tipo · Cantidad · "
            "Importe · Total (agregás filas con + AGREGAR), las "
            "**SECCIONES** GASTOS, CAJA, TARJETAS y TRANSFERENCIAS, los "
            "**CHEQUES** (cliente, N.º de cheque, banco, fecha de "
            "emisión, fecha de cobro e "
            "importe) y las **OBSERVACIONES**.",
            "**TARJETAS y TRANSFERENCIAS se precargan solas** con las "
            "ventas del día y cualquier campo se corrige a mano; "
            "**el DETALLE también se precarga** con lo vendido por "
            "producto (cantidad y precio unitario); "
            "**PRECARGAR DEL DÍA** las vuelve a traer y **LIMPIAR TODO** "
            "arranca de cero.",
            "En la pestaña 2 contás los billetes de $100 a $20.000: cada "
            "fila calcula **Cantidad × valor = importe** y al final cierra "
            "el **TOTAL EFECTIVO**. Ese total **se copia solo** al campo "
            "**EFECTIVO** de la pestaña 1 y a la planilla impresa, así no "
            "hay que escribirlo dos veces.",
            "APRETÁ **GUARDAR RENDICIÓN** para que quede guardada la del "
            "día (hay **un registro por fecha**: se actualiza y nunca se "
            "duplica) y **GENERAR PLANILLA A4** para obtener el archivo "
            "con las secciones, los cheques, el conteo de billetes y las "
            "observaciones, listo para imprimir en **una sola hoja A4 "
            "horizontal** y llenando la hoja de punta a punta. El **detalle "
            "de venta** no se imprime: sigue "
            "cargándose y guardándose en la pantalla, pero en el papel no "
            "aparece.",
        ],
        seccion="sección 21 del manual",
        ejemplos=["¿Cómo cargo la rendición?",
                  "¿Cómo uso la calculadora de billetes?",
                  "¿Cómo imprimo la planilla en A4?"],
    ),
    dict(
        id="historial",
        titulo="Historial de cierres y detalle de un cierre",
        claves="historial cierres cerrados detalle ver dias anteriores "
               "tabla doble clic",
        frases=["historial de cierres", "ver el detalle", "cierres pasados",
                "detalle del cierre"],
        parrafos=[
            "**Historial de cierres** lista cada día con fecha, total "
            "vendido, efectivo, transferencias, tarjetas (débito + "
            "crédito), diferencia y estado (cuadrada / sobrante / "
            "faltante).",
            "Con doble clic o con **Ver detalle** se abre el cierre "
            "completo: totales con el desglose de tarjetas, arqueo de "
            "billetes, detalle de transferencias y las ventas registradas. "
            "También indica quién abrió y quién cerró.",
            "Ahí mismo está el botón **Reabrir caja (contraseña)** para el "
            "rango DESARROLLADOR.",
        ],
        seccion="sección 8 del manual",
        ejemplos=["¿Dónde veo los cierres anteriores?",
                  "¿Cómo veo el detalle de un cierre?"],
    ),
    dict(
        id="estadisticas",
        titulo="Estadísticas y filtros por fecha",
        claves="estadisticas estadistica venta ventas filtros filtro fecha "
               "rango hoy ultimos semana mes promedio grafico graficos "
               "barras recaudado consultar cuanto vendi totales",
        frases=["estadisticas", "cuanto vendi", "filtro por fecha",
                "ultimos 7 dias", "este mes"],
        parrafos=[
            "**Estadísticas** tiene filtros por fecha: un día específico o "
            "un rango, con los atajos **Hoy**, **Últimos 7 días**, **Este "
            "mes** y **Todo**.",
            "Muestra total de ventas, venta promedio, garrafas por tipo, "
            "total recaudado, lo cobrado en efectivo / transferencia / "
            "tarjetas (con su desglose), cantidad de transferencias, un "
            "gráfico de barras por día y el resumen de cierres del período.",
            "Es una sección del rango **DESARROLLADOR**: si no te aparece en "
            "el lateral es un permiso, y un administrador puede habilitártela "
            "en Administración.",
        ],
        seccion="sección 9 del manual",
        ejemplos=["¿Cuánto vendí este mes?",
                  "¿Por qué no me aparecen las Estadísticas?"],
    ),
    dict(
        id="usuarios",
        titulo="Usuarios, rangos y permisos",
        claves="usuario usuarios alta baja crear eliminar activar "
               "desactivar rango rangos permiso permisos casilla casillas "
               "administracion panel administrar contrasena nueva clave "
               "acceso desarrollador operario",
        frases=["crear usuario", "usuario nuevo", "permisos de este usuario",
                "asignar permisos", "panel de administracion",
                "activar usuario", "desactivar usuario"],
        parrafos=[
            "El panel **Panel de control** (solo "
            "DESARROLLADOR) sirve para crear, modificar, activar/desactivar "
            "y eliminar usuarios, asignar rangos y contraseñas y ver el "
            "registro de actividad.",
            "Al crear o modificar un usuario aparece **PERMISOS DE ESTE "
            "USUARIO** con casillas agrupadas (CAJAS, VENTAS Y COBROS, "
            "SECCIONES, REPORTES Y PERFIL). Si marcás casillas, ese usuario "
            "usa exactamente esas; si no marcás ninguna, usa los permisos "
            "de su rango. **DESARROLLADOR** siempre tiene todos.",
            "No se puede eliminar al último DESARROLLADOR, ni desactivar tu "
            "propia sesión, ni repetir nombres de usuario.",
        ],
        seccion="secciones 13 y 14 del manual",
        ejemplos=["¿Cómo creo un usuario nuevo?",
                  "¿Cómo le doy permisos a un usuario?"],
    ),
    dict(
        id="mi_cuenta",
        titulo="Mi cuenta: foto de perfil y contraseña",
        claves="mi cuenta perfil foto imagen avatar quitar datos ultimo "
               "acceso cambiar contrasena clave olvide olvide cerrar sesion",
        frases=["mi cuenta", "foto de perfil", "cambiar mi contrasena",
                "cambiar la contrasena", "subir foto", "quitar foto",
                "olvide la contrasena"],
        parrafos=[
            "**Mi cuenta** muestra tu **foto de perfil** (**Elegir "
            "imagen…**, se recorta en cuadrado y se reduce; **Quitar "
            "foto**), tus datos (usuario, rango, último acceso y fecha de "
            "creación), el cambio de contraseña y **Cerrar sesión**.",
            "**Cada usuario tiene su propia foto**: se guarda en la carpeta "
            "`perfiles/` con un archivo por usuario, así que no se pisa con "
            "la de nadie. Si tenés foto también se ve en el lateral.",
            "La contraseña se pide **actual, nueva y su repetición** "
            "(mínimo 4 caracteres). Si la olvidaste, un DESARROLLADOR te "
            "puede crear una nueva desde Administración.",
        ],
        seccion="sección 18 del manual",
        ejemplos=["¿Cómo cambio mi contraseña?",
                  "¿Cómo pongo una foto de perfil?"],
    ),
    dict(
        id="respaldos",
        titulo="Respaldos y restauración de los datos",
        claves="respaldo respaldos respaldar backup copia seguridad "
               "restaurar restauracion perdi datos carpeta garrafas base "
               "automatico pendrive nube",
        frases=["respaldar ahora", "restaurar respaldo", "copia de seguridad",
                "carpeta de respaldos", "perdi los datos"],
        parrafos=[
            "Los respaldos se guardan solos en la carpeta **respaldos/**, "
            "junto al programa: al abrir el programa (uno por día), al "
            "cerrarlo si falta y **en cada cierre de caja**. Se conservan "
            "los últimos **60**.",
            "En **Configuración → Respaldo de la base de datos** hay "
            "**Respaldar ahora**, **Abrir carpeta de respaldos** y "
            "**Restaurar respaldo…** (primero hace un respaldo de "
            "seguridad de la base actual). Después de restaurar, reiniciá "
            "el programa.",
            "También conviene copiar `garrafas.db` a un pendrive o a la nube "
            "de vez en cuando: ahí está todo.",
        ],
        seccion="sección 17 del manual",
        ejemplos=["¿Cómo respaldo los datos?",
                  "¿Cómo restauro un respaldo?"],
    ),
    dict(
        id="productos",
        titulo="Productos, precios y configuración",
        claves="producto productos precio precios cambiar cambio configura "
               "configuracion editar precio garrafa garrafas kilo kg 10 15 "
               "45 15me me eco propano envase envases modificar valor "
               "fondo general",
        frases=["cambiar el precio", "editar precios", "configuracion",
                "productos y precios", "agregar producto", "agrego un producto",
                "producto nuevo", "eco propano",
                "agregar envase"],
        parrafos=[
            "En **Configuración → Productos** cargás los productos y sus "
            "precios. Ya vienen **Garrafa 10 kg, 15 kg, ME, 45 kg y "
            "ECO PROPANO** más los **envases sueltos** (10 kg, 15 kg, "
            "45 kg, ME y ECO PROPANO) con precios de ejemplo.",
            "Hay que distinguir las dos familias: las **garrafas con gas** "
            "van al recuadro **VENTA DE GARRAFAS (con gas)** del Excel y los "
            "**envases sueltos** van al recuadro aparte **VENTA DE "
            "ENVASES**. El programa las separa solo: todo producto que "
            "empieza con “Envase” es envase suelto.",
            "Ahí mismo están el **fondo inicial** general y otros "
            "parámetros. Solo el rango **DESARROLLADOR** puede modificar "
            "precios y configuración.",
        ],
        seccion="sección 1 del manual",
        ejemplos=["¿Cómo cambio el precio de una garrafa?",
                  "¿Cómo agrego un producto nuevo?",
                  "¿Qué diferencia hay entre envase y garrafa?"],
    ),
    dict(
        id="nuevo_dia",
        titulo="Nuevo día y cajas de otra fecha",
        claves="nuevo medianoche cambio fecha ayer otra caja combo "
               "seleccionar fecha automatico automática amanecio sin cerrar",
        frases=["nuevo dia", "cruzo la medianoche", "caja de ayer",
                "ver caja de la fecha", "cajas sin cerrar"],
        parrafos=[
            "Al abrir el programa en una fecha nueva (o si cruzás la "
            "medianoche con el programa abierto) se **crea sola una caja "
            "nueva**, con los contadores en cero y separada del día "
            "anterior.",
            "Si alguna caja anterior quedó abierta, aparece un aviso en "
            "**Inicio**. Desde el combo **Ver caja de la fecha** podés "
            "seleccionar cualquier caja para verla o cerrarla; si elegiste "
            "una fecha a mano, el programa no te devuelve a la de hoy.",
        ],
        seccion="sección 7 del manual",
        ejemplos=["Se cruzó la medianoche, ¿qué pasa con la caja?",
                  "¿Cómo veo la caja de ayer?"],
    ),
    dict(
        id="problemas",
        titulo="No me deja hacer algo (errores comunes)",
        claves="error errores problema problemas falla falla no nofunciona "
               "funciona raro pasa pasaalgo nomebloquea bloquea revisar "
               "avisó aviso aparece aparece boton botones oculto falta "
               "lateral menu",
        frases=["no me deja", "no puedo", "no funciona", "me sale error",
                "no me aparece", "que pasa si", "esta roto"],
        parrafos=[
            "Antes que nada fijate estas tres cosas, que resuelven casi "
            "todo: **1)** la caja del día está **abierta** (sin apertura no "
            "se cargan ventas); **2)** tu usuario tiene el **permiso** "
            "correspondiente (si un botón no aparece es eso); **3)** la caja "
            "no está **cerrada** (una caja cerrada queda bloqueada hasta "
            "que un DESARROLLADOR la reabra).",
            "Los intentos de sesión, las ventas y los cierres quedan en "
            "**Administración → Registro de actividad**, así que ahí se ve "
            "exactamente qué pasó y quién lo hizo.",
        ],
        seccion="secciones 6, 13 y 16 del manual",
        ejemplos=["No me deja registrar ventas",
                  "No me aparece un botón del menú"],
    ),
    dict(
        id="actividad",
        titulo="Registro de actividad (trazabilidad)",
        claves="actividad registro historial acciones trazabilidad quien "
               "usuario qué hizo auditoria columna registro mostró",
        frases=["registro de actividad", "quien hizo que", "quien hizo",
                "quien abrio", "quien registro la venta",
                "que hizo cada usuario", "columna registro"],
        parrafos=[
            "**Administración → Registro de actividad** muestra fecha, "
            "hora, usuario, acción y detalle de cada evento: inicios de "
            "sesión (y los rechazados), ventas registradas / modificadas / "
            "eliminadas, aperturas, cierres, reaperturas, altas y bajas de "
            "usuarios, cambios de contraseña y exportaciones a Excel.",
            "Además, en **Ventas** la columna **Registró** dice quién "
            "cargó cada venta, y el detalle del cierre indica quién abrió y "
            "quién cerró.",
        ],
        seccion="sección 16 del manual",
        ejemplos=["¿Quién cargó esta venta?",
                  "¿Dónde veo quién hizo cada cosa?"],
    ),
    dict(
        id="instalar",
        titulo="Instalar el programa o llevarlo a otra PC",
        claves="instalar instalo instalar exe ejecutable otra pc "
               "computadora windows python compilar compilacion pyinstaller "
               "iniciar bat descarga descargar copiar carpeta",
        frases=["llevarlo a otra pc", "instalar el programa",
                "generar el exe", "compilar", "no tengo python"],
        parrafos=[
            "La forma más fácil es copiar **MOSTRADOR.exe**: en la otra PC "
            "**no hace falta tener Python**, se ejecuta y listo. Los datos "
            "se guardan en `garrafas.db`, junto al `.exe`.",
            "Para llevar los datos ya cargados, copiá también `garrafas.db` "
            "(y la carpeta `respaldos/`). Si la otra PC empieza de cero, "
            "basta el `.exe`.",
            "Para regenerar el `.exe` después de cambiar el código: doble "
            "clic en **Compilar MOSTRADOR.bat**. O copiá la carpeta "
            "completa y usá **Python 3** con `Iniciar.bat`.",
        ],
        seccion="apartado «Llevarlo a otra PC» del manual",
        ejemplos=["¿Cómo lo instalo en otra computadora?",
                  "¿Hace falta Python para usarlo?"],
    ),
    dict(
        id="ayuda_general",
        titulo="Qué hace este programa",
        claves="programa sistema hace sirve resumen general como funciona "
               "para que sirve descripcion inicio rapido",
        frases=["que hace este programa", "para que sirve",
                "como funciona el sistema", "de que se trata"],
        parrafos=[
            "Controla el día a día de la venta de garrafas: registra "
            "ventas, abre y cierra la caja con arqueo de billetes, guarda "
            "el historial de cierres, muestra estadísticas y exporta todo a "
            "Excel imprimible en A4.",
            "El circuito de siempre es: **abrir caja** (Inicio) → "
            "**registrar ventas** (Ventas) → **cerrar caja con arqueo** "
            "(Inicio). Todo queda asociado al usuario que lo hizo.",
            "Preguntame directo, por ejemplo: «¿Cómo abro la caja?», "
            "«¿Cómo exporto a Excel?» o «¿Qué hago si falta plata en el "
            "arqueo?».",
        ],
        seccion="el manual completo del sistema",
        ejemplos=["¿Para qué sirve este programa?"],
    ),
]

# Mensaje de bienvenida / saludo (cuando la pregunta no tiene palabras)
SALUDO = dict(
    id="saludo",
    titulo="Hola, estoy para ayudarte",
    parrafos=[
        "Soy el **soporte del sistema** y respondo con la documentación "
        "misma del programa: no necesito internet ni cuesto nada por "
        "consulta.",
        "Preguntame, por ejemplo: «¿Cómo abro la caja?», «¿Cómo exporto a "
        "Excel?» o «¿Qué significa FALTANTE?».",
    ],
    seccion="sección de ayuda del manual",
    ejemplos=["¿Cómo abro la caja del día?",
              "¿Cómo cierro la caja?",
              "¿Cómo exporto a Excel?"],
)

# Preguntas rápidas que se muestran como botones
SUGERENCIAS = [
    "¿Cómo abro la caja del día?",
    "¿Cómo cierro la caja?",
    "No me deja registrar ventas",
    "¿Cómo exporto a Excel?",
    "¿Cómo cargo la planilla de rendición?",
    "¿Cómo creo un usuario nuevo?",
    "¿Cómo respaldo los datos?",
]


# --------------------------------------------------------------- preparación
def _preparar(tema):
    base = tema["titulo"] + " " + tema["claves"]
    tema["_toks"] = set(tokens(base))
    tema["_lista"] = sorted(tema["_toks"])
    tema["_frases"] = [normalizar(f) for f in tema.get("frases", [])]
    return tema


for _t in TEMAS:
    _preparar(_t)


def _puntuar(qtoks, qnorm, tema):
    punt = 0
    for frase in tema["_frases"]:
        if frase and frase in qnorm:
            punt += 6                      # acertó una pregunta completa
    for palabra in qtoks:
        if palabra in tema["_toks"]:
            punt += 3                      # palabra clave exacta
        elif _parecido(palabra, tema["_lista"]):
            punt += 1                      # parecida (typos / conjugación)
    return punt


def resolver(pregunta):
    """
    Devuelve dict con: ok, tema, puntaje, ambiguas, saludo.
    Si la pregunta está vacía o es un saludo, responde con SALUDO.
    """
    qnorm = normalizar(pregunta)
    qtoks = tokens(qnorm)
    if not qtoks:
        return {"ok": True, "tema": SALUDO, "puntaje": 0,
                "ambiguas": [], "saludo": True}

    puntajes = [(_t, _puntuar(qtoks, qnorm, _t)) for _t in TEMAS]
    puntajes.sort(key=lambda x: -x[1])
    mejor, punt = puntajes[0]

    if punt < UMBRAL:
        return {"ok": False, "tema": None, "puntaje": punt,
                "ambiguas": [], "saludo": False}

    empates = [t for t, p in puntajes if p == punt and p > 0]
    if len(empates) > 1:
        # Pregunta vaga ("caja"): mejor mostrar por dónde empezar
        return {"ok": False, "tema": None, "puntaje": punt,
                "ambiguas": empates, "saludo": False}

    return {"ok": True, "tema": mejor, "puntaje": punt,
            "ambiguas": empates, "saludo": False}


def buscar(pregunta):
    """Atajo: devuelve (tema, puntaje); tema es None si no encontró."""
    r = resolver(pregunta)
    return r["tema"], r["puntaje"]


def alternativas(pregunta, cantidad=6):
    """Temas ordenados por puntaje, para sugerir cuando no se entendió."""
    qnorm = normalizar(pregunta)
    qtoks = tokens(qnorm)
    if not qtoks:
        return []
    puntajes = [(_t, _puntuar(qtoks, qnorm, _t)) for _t in TEMAS]
    puntajes.sort(key=lambda x: -x[1])
    return [t for t, p in puntajes if p > 0][:cantidad]


def ejemplos_de(temas, cantidad=6):
    """Preguntas de ejemplo de una lista de temas (sin repetir)."""
    salida, vistos = [], set()
    for t in temas:
        for e in t.get("ejemplos", []):
            if e not in vistos:
                vistos.add(e)
                salida.append(e)
            if len(salida) >= cantidad:
                return salida
    return salida
