# -*- coding: utf-8 -*-
"""
ASISTENTE VIRTUAL de soporte (robot de ayuda del sistema).

Ventana de chat flotante con burbujas, avatar de robot, indicador de
"escribiendo…" y respuestas con botones. No usa internet: busca en la base
de conocimiento local (ayuda.py), así que funciona sin conexión, no cuesta
nada por consulta y nunca inventa respuestas fuera de la documentación.

La lógica de búsqueda (ayuda.resolver / ayuda.alternativas) no cambia.
"""

import datetime
import random
import re
import tkinter as tk
import tkinter.font as tkfont

import ayuda
import estilos as st
import iconos as ic
from widgets_figma import Tarjeta

# Preguntas rápidas: (etiqueta corta del botón, pregunta que se envía)
CHIPS = [
    ("Abrir caja", "¿Cómo abro la caja del día?"),
    ("Cerrar caja", "¿Cómo cierro la caja?"),
    ("Registrar venta", "¿Cómo registro una venta?"),
    ("Exportar Excel", "¿Cómo exporto a Excel?"),
    ("Usuarios", "¿Cómo creo un usuario nuevo?"),
    ("Respaldos", "¿Cómo respaldo los datos?"),
]

# Corta los **negritas** y *cursivas* del texto armado a mano
_PARTES = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")

AZUL_SUAVE = "#EAF1FE"
VERDE_ONLINE = "#22C55E"
GRIS_HORA = "#94A3B8"
TAM = 10                        # tamaño de letra de las burbujas


def _trozos(texto):
    """Divide el texto en (trozo, estilo) con estilo: '', 'b' (negrita) o 'i'."""
    salida = []
    for parte in _PARTES.split(texto):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**") and len(parte) > 4:
            salida.append((parte[2:-2], "b"))
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            salida.append((parte[1:-1], "i"))
        else:
            salida.append((parte, ""))
    return salida


class _Chip(Tarjeta):
    """Botón en forma de píldora (sugerencias y opciones del asistente)."""

    def __init__(self, parent, texto, comando, izquierda=False):
        super().__init__(parent, fondo=st.TARJETA, borde="#CFDAF0", radio=15,
                         padx=10, pady=6, exterior=st.FONDO)
        self._cmd = comando
        self.lbl = tk.Label(self.cuerpo, text=texto, bg=st.TARJETA,
                            fg=st.ACENTO_OSCURO, font=(st.FUENTE, 9, "bold"),
                            cursor="hand2", justify="left")
        if izquierda:
            self.lbl.pack(anchor="w")
        else:
            self.lbl.pack()
        for w in (self, self.cuerpo, self.lbl):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self._clic)
            w.bind("<Enter>", lambda e: self._color(AZUL_SUAVE))
            w.bind("<Leave>", lambda e: self._color(st.TARJETA))

    def _color(self, c):
        self.pintar(fondo=c)
        self.lbl.configure(bg=c)

    def _clic(self, _e=None):
        if self._cmd:
            self._cmd()


class SoporteVentana(tk.Toplevel):
    """Chat de ayuda que se superpone a la pantalla que estés usando."""

    def __init__(self, app, boton=None):
        super().__init__(app)
        self.app = app
        self.title("Asistente DOBLE G SRL — Soporte")
        self.configure(bg=st.FONDO)

        # Tamaño adaptado a la pantalla; se abre junto al botón que la llamó
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(450, max(380, sw - 60))
        alto = min(720, max(480, sh - 90))
        self._ancho_ventana = ancho
        x = max(0, sw - ancho - 20)
        y = max(0, sh - alto - 56)
        if boton is not None:
            try:
                bx = boton.winfo_rootx()
                by = boton.winfo_rooty()
                x = max(0, min(bx - ancho + 40, sw - ancho - 20))
                y = max(0, min(by + 40, sh - alto - 56))
            except tk.TclError:
                pass
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(380, ancho), min(480, alto))

        # Se superpone a la ventana principal pero no la bloquea (sin grab)
        self.transient(app)
        self.update_idletasks()
        self._ajustar_a_pantalla()

        # Estado del chat
        self._pensando = False
        self._cola = []             # preguntas / mensajes esperando turno
        self._anim = None

        self._construir()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        # La rueda del mouse hace scroll en el chat y no en la pantalla de
        # atrás: devolver "break" corta la cadena de bind_all del programa.
        self.bind("<MouseWheel>", self._rueda_chat)
        self._bienvenida()

    def _ajustar_a_pantalla(self):
        """Corrige la posición si la ventana se pasa del borde del monitor."""
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            ax, ay = self.winfo_rootx(), self.winfo_rooty()
            aw, ah = self.winfo_width(), self.winfo_height()
            dx = dy = 0
            if ax < 0:
                dx = -ax
            elif ax + aw > sw:
                dx = sw - ax - aw
            if ay < 0:
                dy = -ay
            elif ay + ah > sh:
                dy = sh - ay - ah
            if dx or dy:
                self.geometry(f"+{max(0, self.winfo_x() + dx)}+"
                              f"{max(0, self.winfo_y() + dy)}")
                self.update_idletasks()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ UI
    def _construir(self):
        SB = st.SIDEBAR

        # -------- cabecera: robot + nombre + estado --------
        cab = tk.Frame(self, bg=SB)
        cab.pack(side="top", fill="x")

        izq = tk.Frame(cab, bg=SB)
        izq.pack(side="left", padx=(16, 0), pady=12)
        avatar = tk.Label(izq, bg=SB, image=ic.cuadro(
            "robot", 46, "#FFFFFF", st.ACENTO, 23, 26, 1.7))
        avatar.pack(side="left")
        tk.Label(avatar, text="\u25cf", fg=VERDE_ONLINE, bg=SB,
                 font=(st.FUENTE, 9)).place(relx=1.0, rely=1.0, anchor="se",
                                            x=2, y=2)
        col = tk.Frame(izq, bg=SB)
        col.pack(side="left", padx=(12, 0))
        tk.Label(col, text="Asistente DOBLE G SRL", bg=SB, fg="#FFFFFF",
                 font=(st.FUENTE, 12, "bold")).pack(anchor="w")
        est = tk.Frame(col, bg=SB)
        est.pack(anchor="w")
        tk.Label(est, text="\u25cf", fg=VERDE_ONLINE, bg=SB,
                 font=(st.FUENTE, 7)).pack(side="left", padx=(0, 5))
        tk.Label(est, text="En línea · responde sin internet", bg=SB,
                 fg="#9FB0CC", font=(st.FUENTE, 8)).pack(side="left")

        der = tk.Frame(cab, bg=SB)
        der.pack(side="right", padx=(0, 10))
        self._icono_cab(der, "x", "Cerrar", self._al_cerrar).pack(side="right")
        self._icono_cab(der, "refresh", "Nueva conversación",
                        self._limpiar).pack(side="right")

        # -------- sugerencias (preguntas rápidas) --------
        marco_chips = tk.Frame(self, bg=st.FONDO)
        marco_chips.pack(side="top", fill="x", padx=14, pady=(12, 4))
        tk.Label(marco_chips, text="SUGERENCIAS", bg=st.FONDO,
                 fg=st.TEXTO_SUAVE, font=(st.FUENTE, 8, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        for c in range(3):
            marco_chips.columnconfigure(c, weight=1, uniform="chip")
        for i, (etiqueta, pregunta) in enumerate(CHIPS):
            chip = _Chip(marco_chips, etiqueta,
                         lambda p=pregunta: self.preguntar(p))
            chip.grid(row=1 + i // 3, column=i % 3, sticky="ew",
                      padx=(0 if i % 3 == 0 else 3, 0 if i % 3 == 2 else 3),
                      pady=(0, 6))

        # -------- caja de escribir (se empaqueta antes que el chat) --------
        pie = tk.Frame(self, bg=st.TARJETA)
        pie.pack(side="bottom", fill="x")
        tk.Frame(pie, bg=st.BARRA_BORDE, height=1).pack(fill="x")
        fila = tk.Frame(pie, bg=st.TARJETA)
        fila.pack(fill="x", padx=14, pady=12)

        self._img_enviar = ic.cuadro("send", 40, "#FFFFFF", st.ACENTO, 20, 20, 1.8)
        self._img_enviar_h = ic.cuadro("send", 40, "#FFFFFF", st.ACENTO_OSCURO, 20, 20, 1.8)
        btn = tk.Label(fila, image=self._img_enviar, bg=st.TARJETA, cursor="hand2")
        btn.pack(side="right", padx=(10, 0))
        btn.bind("<Button-1>", lambda e: self._enviar())
        btn.bind("<Enter>", lambda e: btn.config(image=self._img_enviar_h))
        btn.bind("<Leave>", lambda e: btn.config(image=self._img_enviar))

        caja = Tarjeta(fila, fondo=st.TARJETA, borde="#D9E0EC", radio=20,
                       padx=16, pady=9, exterior=st.TARJETA)
        caja.pack(side="left", fill="x", expand=True)
        self.var_pregunta = tk.StringVar()
        self.entrada = tk.Entry(
            caja.cuerpo, textvariable=self.var_pregunta, font=(st.FUENTE, 11),
            relief="flat", bd=0, bg=st.TARJETA, fg=st.TEXTO,
            insertbackground=st.TEXTO, highlightthickness=0)
        self.entrada.pack(fill="x")
        self.entrada.bind("<Return>", lambda e: self._enviar())
        self._ph = tk.Label(caja.cuerpo, text="Escribí tu pregunta…",
                            bg=st.TARJETA, fg=GRIS_HORA, font=(st.FUENTE, 11))
        self._ph.place(x=0, y=0)
        self._ph.bind("<Button-1>", lambda e: self.entrada.focus_set())
        self.var_pregunta.trace_add("write", self._actualizar_placeholder)

        # -------- conversación (burbujas) --------
        marco = tk.Frame(self, bg=st.FONDO)
        marco.pack(side="top", fill="both", expand=True)
        self.lienzo = tk.Canvas(marco, bg=st.FONDO, highlightthickness=0, bd=0)
        barra = tk.Scrollbar(marco, orient="vertical", command=self.lienzo.yview)
        try:
            from tkinter import ttk
            barra.destroy()
            barra = ttk.Scrollbar(marco, orient="vertical",
                                  command=self.lienzo.yview,
                                  style="Fino.Vertical.TScrollbar")
        except Exception:
            pass
        self.lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.hilo = tk.Frame(self.lienzo, bg=st.FONDO)
        self._ventana_hilo = self.lienzo.create_window((0, 0), window=self.hilo,
                                                       anchor="nw")
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(
            self._ventana_hilo, width=e.width))
        self.hilo.bind("<Configure>", lambda e: self.lienzo.configure(
            scrollregion=self.lienzo.bbox("all")))

    def _icono_cab(self, parent, nombre, ayuda_txt, comando):
        img = ic.icono(nombre, 18, "#C7D2E4", 1.8)
        img_h = ic.icono(nombre, 18, "#FFFFFF", 1.8)
        b = tk.Label(parent, image=img, bg=st.SIDEBAR, cursor="hand2",
                     padx=9, pady=9)
        b.bind("<Button-1>", lambda e: comando())
        b.bind("<Enter>", lambda e: b.config(image=img_h, bg="#22304D"))
        b.bind("<Leave>", lambda e: b.config(image=img, bg=st.SIDEBAR))
        return b

    def _actualizar_placeholder(self, *_):
        if self.var_pregunta.get():
            self._ph.place_forget()
        else:
            self._ph.place(x=0, y=0)

    # ------------------------------------------------------------- ventana
    def _rueda_chat(self, evento):
        delta = int(-evento.delta / 120)
        if delta:
            self.lienzo.yview_scroll(delta, "units")
        return "break"                    # no scrollea la pantalla de atrás

    def _al_cerrar(self):
        """Se oculta (no se destruye) para conservar la conversación."""
        try:
            self.withdraw()
        except tk.TclError:
            pass

    def mostrar(self):
        self.deiconify()
        self.lift()
        self._ajustar_a_pantalla()
        self.focus_set()
        self.entrada.focus_set()

    # ------------------------------------------------------------ burbujas
    def _ancho_chat(self):
        w = self.lienzo.winfo_width()
        if w < 150:
            w = self._ancho_ventana - 16
        return w

    def _hora(self):
        return datetime.datetime.now().strftime("%H:%M")

    def _fila(self, usuario=False):
        """Fila del chat. Devuelve (fila, columna donde va la burbuja)."""
        fila = tk.Frame(self.hilo, bg=st.FONDO)
        fila.pack(fill="x", padx=12, pady=(0, 8))
        if usuario:
            col = tk.Frame(fila, bg=st.FONDO)
            col.pack(side="right")
            return fila, col
        tk.Label(fila, bg=st.FONDO, image=ic.cuadro(
            "robot", 30, "#FFFFFF", st.ACENTO, 15, 17, 1.6)
        ).pack(side="left", anchor="n", padx=(0, 8))
        col = tk.Frame(fila, bg=st.FONDO)
        col.pack(side="left", anchor="n")
        return fila, col

    def _burbuja(self, parent, texto, usuario=False):
        """Burbuja redondeada con texto (soporta **negrita** y *cursiva*)."""
        fondo = st.ACENTO if usuario else st.TARJETA
        fg = "#FFFFFF" if usuario else st.TEXTO
        b = Tarjeta(parent, fondo=fondo, borde=None if usuario else st.BORDE,
                    sin_borde=usuario, radio=14, padx=13, pady=9,
                    exterior=st.FONDO)
        if usuario:
            maxpx = int(self._ancho_chat() * 0.74)
        else:
            maxpx = self._ancho_chat() - 24 - 38 - 2 * b.padx - 8
        maxpx = max(150, maxpx)

        f_n = tkfont.Font(family=st.FUENTE, size=TAM)
        f_b = tkfont.Font(family=st.FUENTE, size=TAM, weight="bold")
        f_i = tkfont.Font(family=st.FUENTE, size=TAM, slant="italic")
        fuentes = {"": f_n, "b": f_b, "i": f_i}

        # Simula el ajuste de líneas para calcular ancho y alto exactos
        parrafos = []
        for linea in texto.split("\n"):
            palabras = []
            for trozo, estilo in _trozos(linea):
                for p in re.findall(r"\S+|\s+", trozo):
                    palabras.append((p, fuentes[estilo]))
            parrafos.append(palabras)
        espacio = f_n.measure(" ")
        mejor = 0
        lineas = 0
        for palabras in parrafos:
            actual = 0
            n = 1
            for p, f in palabras:
                w = espacio if p.isspace() else f.measure(p)
                if p.isspace():
                    if actual:
                        actual += w
                    continue
                if actual and actual + w > maxpx:
                    mejor = max(mejor, actual)
                    n += 1
                    actual = w
                else:
                    actual += w
            mejor = max(mejor, actual)
            lineas += n
        px = min(maxpx, mejor + 8)

        txt = tk.Text(b.cuerpo, wrap="word", bd=0, highlightthickness=0,
                      relief="flat", bg=fondo, fg=fg, font=(st.FUENTE, TAM),
                      padx=0, pady=0, cursor="arrow", takefocus=0,
                      width=max(4, int(px / max(1, f_n.measure("0"))) + 1),
                      height=max(1, lineas))
        txt.tag_configure("b", font=(st.FUENTE, TAM, "bold"))
        txt.tag_configure("i", font=(st.FUENTE, TAM, "italic"))
        for i, linea in enumerate(texto.split("\n")):
            if i:
                txt.insert("end", "\n")
            for trozo, estilo in _trozos(linea):
                txt.insert("end", trozo, estilo or ())
        txt.pack(anchor="w")
        txt.configure(state="disabled")

        # Afina el alto con la medida real del Text (si es confiable)
        try:
            txt.update_idletasks()
            real = txt.count("1.0", "end", "displaylines")
            if real and 0 < real[0] <= lineas:
                txt.configure(height=real[0])
        except tk.TclError:
            pass
        b.configure(width=txt.winfo_reqwidth() + 2 * b.padx)
        return b

    def _bot(self, texto, fuente=None):
        fila, col = self._fila()
        self._burbuja(col, texto).pack(anchor="w")
        if fuente:
            tk.Label(col, text=fuente, bg=st.FONDO, fg=st.ACENTO,
                     font=(st.FUENTE, 8, "italic")).pack(anchor="w", pady=(3, 0))
        tk.Label(col, text=self._hora(), bg=st.FONDO, fg=GRIS_HORA,
                 font=(st.FUENTE, 7)).pack(anchor="w", pady=(2, 0))
        self._al_final()
        return col

    def _usuario(self, texto):
        fila, col = self._fila(usuario=True)
        self._burbuja(col, texto, usuario=True).pack(anchor="e")
        tk.Label(col, text=self._hora(), bg=st.FONDO, fg=GRIS_HORA,
                 font=(st.FUENTE, 7)).pack(anchor="e", pady=(2, 0))
        self._al_final()

    def _opciones(self, col, opciones):
        """Botones (píldoras) debajo de una burbuja: [(texto, comando), ...]."""
        for texto, cmd in opciones:
            _Chip(col, texto, cmd, izquierda=True).pack(anchor="w", pady=(6, 0),
                                                        fill="x")
        self._al_final()

    def _al_final(self):
        try:
            self.update_idletasks()
            self.lienzo.configure(scrollregion=self.lienzo.bbox("all"))
            self.lienzo.yview_moveto(1.0)
        except tk.TclError:
            pass

    # ------------------------------------------- "escribiendo…" y turnos
    def _escribiendo(self):
        fila, col = self._fila()
        b = Tarjeta(col, borde=st.BORDE, radio=14, padx=14, pady=10,
                    ancho=76, exterior=st.FONDO)
        b.pack(anchor="w")
        puntos = []
        for _ in range(3):
            p = tk.Label(b.cuerpo, text="\u25cf", bg=st.TARJETA, fg="#C5CEDD",
                         font=(st.FUENTE, 8))
            p.pack(side="left", padx=2)
            puntos.append(p)

        estado = {"i": 0}

        def animar():
            try:
                for k, p in enumerate(puntos):
                    p.config(fg=st.ACENTO if k == estado["i"] % 3 else "#C5CEDD")
                estado["i"] += 1
                self._anim = self.after(260, animar)
            except tk.TclError:
                pass

        animar()
        self._al_final()
        return fila

    def _responder(self, accion, demora=None):
        """Muestra 'escribiendo…' un instante y después ejecuta la acción."""
        self._pensando = True
        fila = self._escribiendo()
        ms = demora if demora is not None else random.randint(450, 900)

        def listo():
            try:
                if self._anim:
                    self.after_cancel(self._anim)
                    self._anim = None
                fila.destroy()
                self._pensando = False
                accion()
            except tk.TclError:
                return
            self._siguiente()

        self.after(ms, listo)

    def _siguiente(self):
        if self._cola and not self._pensando:
            item = self._cola.pop(0)
            if callable(item):
                self._responder(item)
            else:
                self._responder_pregunta(item)

    # ------------------------------------------------------------ mensajes
    def _bienvenida(self):
        try:
            import database as db
            u = db.usuario_sesion()
            nombre = u["usuario"] if u else ""
        except Exception:
            nombre = ""
        saludo = "¡Hola" + (f", {nombre}" if nombre else "") + \
                 "! Soy el **asistente virtual** de DOBLE G SRL."
        self._responder(lambda: self._bot(saludo), 500)
        self._cola.append(lambda: self._bot(
            "Te explico cómo usar el programa: **caja, ventas, permisos, "
            "Excel, respaldos** y más. Respondo con la documentación real del "
            "sistema, sin internet y sin inventar nada."))
        self._cola.append(lambda: self._bot(
            "Tocá una sugerencia de arriba o escribime tu pregunta abajo."))

    def _limpiar(self):
        """Nueva conversación."""
        self._cola.clear()
        for w in self.hilo.winfo_children():
            w.destroy()
        if not self._pensando:
            self._bienvenida()

    # ------------------------------------------------------------ preguntas
    def _enviar(self):
        texto = self.var_pregunta.get().strip()
        if not texto:
            self.entrada.focus_set()
            return
        self.var_pregunta.set("")
        self.preguntar(texto)

    def preguntar(self, texto):
        """Responde la pregunta que se le hace al soporte."""
        texto = (texto or "").strip()
        if not texto:
            return
        self._usuario(texto)
        if self._pensando or self._cola:
            self._cola.append(texto)
        else:
            self._responder_pregunta(texto)
        self.entrada.focus_set()

    def _responder_pregunta(self, texto):
        r = ayuda.resolver(texto)
        self._responder(lambda: self._mostrar_resultado(texto, r))

    def _mostrar_tema(self, tema):
        partes = []
        if tema["id"] != "saludo":
            partes.append(f"**{tema['titulo']}**")
        partes.extend(tema["parrafos"])
        fuente = None if tema["id"] == "saludo" else f"Fuente: {tema['seccion']}"
        self._bot("\n\n".join(partes), fuente)

    def _elegir_tema(self, tema):
        self._usuario(tema["titulo"])
        self._responder(lambda: self._mostrar_tema(tema))

    def _mostrar_resultado(self, texto, r):
        if r["ok"]:
            self._mostrar_tema(r["tema"])
            return

        if r["ambiguas"]:
            col = self._bot("Encontré **más de un tema** para eso. "
                            "¿Cuál querés ver?")
            self._opciones(col, [
                (t["titulo"], lambda t=t: self._elegir_tema(t))
                for t in r["ambiguas"][:4]])
            return

        col = self._bot(
            "No tengo esa respuesta cargada. No encontré nada en la "
            "documentación del sistema para **" + texto + "**.\n\n"
            "Probá con otras palabras, por ejemplo «caja», «venta», "
            "«excel» o «usuarios».")
        extras = ayuda.alternativas(texto, 3)
        if extras:
            self._opciones(col, [
                (t["titulo"], lambda t=t: self._elegir_tema(t))
                for t in extras])
