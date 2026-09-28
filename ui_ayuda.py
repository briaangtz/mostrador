# -*- coding: utf-8 -*-
"""
Ventana flotante de SOPORTE: responde preguntas sobre el uso del sistema.

No es una IA de internet: busca en la base de conocimiento local
(ayuda.py), así que funciona sin conexión, no cuesta nada por consulta y
nunca inventa respuestas fuera de la documentación del programa.
"""

import re
import tkinter as tk
from tkinter import ttk

import ayuda
import estilos as st

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


class SoporteVentana(tk.Toplevel):
    """Chat de ayuda que se superpone a la pantalla que estés usando."""

    def __init__(self, app, boton=None):
        super().__init__(app)
        self.app = app
        self.title("Soporte — Ayuda del sistema")
        self.configure(bg=st.FONDO)

        # Tamaño adaptado a la pantalla; se abre junto al botón que la llamó
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ancho = min(560, max(380, sw - 60))
        alto = min(700, max(430, sh - 90))
        x = max(0, sw - ancho - 20)
        y = max(0, sh - alto - 56)
        if boton is not None:
            # Se abre al lado del botón que la llamó, sin salirse de pantalla
            try:
                bx = boton.winfo_rootx()
                by = boton.winfo_rooty()
                x = max(0, min(bx + 56, sw - ancho - 20))
                y = max(0, min(by + 56, sh - alto - 56))
            except tk.TclError:
                pass
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(360, ancho), min(400, alto))

        # Se superpone a la ventana principal pero no la bloquea (sin grab)
        self.transient(app)

        # Una vez dibujada se reajusta según la barra de título real, para
        # que nunca quede cortada ni fuera del monitor (punto 4).
        self.update_idletasks()
        self._ajustar_a_pantalla()

        self._construir()
        self._bienvenida()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

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
                nx = max(0, self.winfo_x() + dx)
                ny = max(0, self.winfo_y() + dy)
                self.geometry(f"+{nx}+{ny}")
                self.update_idletasks()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ UI
    def _construir(self):
        # -------- cabecera --------
        cab = tk.Frame(self, bg=st.BARRA)
        cab.pack(fill="x")

        col = tk.Frame(cab, bg=st.BARRA)
        col.pack(side="left", fill="x", expand=True, padx=16, pady=11)
        tk.Label(col, text="SOPORTE", bg=st.BARRA, fg="#ffffff",
                 font=(st.FUENTE, 13, "bold")).pack(anchor="w")
        tk.Label(col, text="Respuestas del propio sistema · sin internet",
                 bg=st.BARRA, fg="#9fb0cc", font=(st.FUENTE, 8)).pack(anchor="w")

        btn_cerrar = tk.Button(
            cab, text="✕", bg=st.BARRA, fg="#c7d2e4", activebackground="#22304d",
            activeforeground="#ffffff", relief="flat", bd=0, padx=14, pady=10,
            font=(st.FUENTE, 13), cursor="hand2", command=self._al_cerrar)
        btn_cerrar.pack(side="right", padx=(0, 8))
        btn_cerrar.bind("<Enter>", lambda e: btn_cerrar.config(bg="#22304d"))
        btn_cerrar.bind("<Leave>", lambda e: btn_cerrar.config(bg=st.BARRA))

        # -------- preguntas rápidas (grilla de 2 columnas: no se cortan) --------
        marco_chips = tk.Frame(self, bg=st.FONDO)
        marco_chips.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(marco_chips, text="PREGUNTAS RÁPIDAS", bg=st.FONDO,
                 fg=st.TEXTO_SUAVE, font=(st.FUENTE, 8, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        marco_chips.columnconfigure(0, weight=1, uniform="c")
        marco_chips.columnconfigure(1, weight=1, uniform="c")
        for i, (etiqueta, pregunta) in enumerate(CHIPS):
            b = tk.Button(
                marco_chips, text=etiqueta, relief="flat", bd=1,
                bg=st.TARJETA, fg=st.ACENTO_OSCURO, activebackground="#dbeafe",
                activeforeground=st.ACENTO_OSCURO, font=(st.FUENTE, 9, "bold"),
                padx=6, pady=6, cursor="hand2", anchor="center",
                command=lambda p=pregunta: self.preguntar(p))
            b.grid(row=1 + i // 2, column=i % 2, sticky="ew",
                   padx=(0 if i % 2 == 0 else 5, 5 if i % 2 == 0 else 0),
                   pady=(0, 5))

        # -------- conversación --------
        marco_chat = tk.Frame(self, bg=st.FONDO)
        marco_chat.pack(fill="both", expand=True, padx=14, pady=(2, 8))
        self.chat = tk.Text(
            marco_chat, wrap="word", bd=0, relief="flat", state="disabled",
            bg=st.FONDO, fg=st.TEXTO, font=(st.FUENTE, 10),
            selectbackground=st.ACENTO, highlightthickness=0, cursor="arrow")
        barra = ttk.Scrollbar(marco_chat, orient="vertical",
                              command=self.chat.yview)
        self.chat.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.chat.pack(side="left", fill="both", expand=True)

        # Etiquetas (el orden importa: las últimas tienen prioridad)
        self.chat.tag_configure(
            "pregunta", background=st.ACENTO, foreground="#ffffff",
            lmargin1=14, lmargin2=14, rmargin=110, justify="left",
            font=(st.FUENTE, 10, "bold"), relief="solid", borderwidth=1,
            spacing1=10, spacing3=12)
        self.chat.tag_configure(
            "respuesta", background=st.TARJETA, foreground=st.TEXTO,
            lmargin1=14, lmargin2=14, rmargin=14, justify="left",
            relief="solid", borderwidth=1, spacing1=6, spacing3=10)
        self.chat.tag_configure(
            "titulo", background=st.TARJETA, foreground=st.ACENTO_OSCURO,
            lmargin1=14, lmargin2=14, rmargin=14, justify="left",
            font=(st.FUENTE, 11, "bold"), relief="solid", borderwidth=1,
            spacing3=2)
        self.chat.tag_configure(
            "sistema", background=st.TARJETA, foreground=st.TEXTO_SUAVE,
            lmargin1=14, lmargin2=14, rmargin=14, justify="left",
            font=(st.FUENTE, 9), relief="solid", borderwidth=1,
            spacing3=10)
        self.chat.tag_configure(
            "fuente", background=st.TARJETA, foreground=st.ACENTO,
            lmargin1=14, lmargin2=14, rmargin=14, justify="left",
            font=(st.FUENTE, 8, "italic"), relief="solid", borderwidth=1,
            spacing3=12)
        self.chat.tag_configure("negrita", font=(st.FUENTE, 10, "bold"))
        self.chat.tag_configure("cursiva", font=(st.FUENTE, 10, "italic"))

        # La rueda del mouse hace scroll en el chat (y no en la pantalla de
        # atrás): devolver "break" corta la cadena de bind_all del programa.
        self.chat.bind("<MouseWheel>", self._rueda_chat)

        # -------- escribir pregunta --------
        pie = tk.Frame(self, bg=st.FONDO)
        pie.pack(fill="x", padx=14, pady=(0, 14))
        self.var_pregunta = tk.StringVar()
        self.entrada = tk.Entry(
            pie, textvariable=self.var_pregunta, font=(st.FUENTE, 11),
            relief="solid", bd=1, bg=st.TARJETA, fg=st.TEXTO,
            highlightcolor=st.ACENTO, highlightthickness=1,
            highlightbackground=st.BORDE)
        self.entrada.pack(side="left", fill="x", expand=True, ipady=7)
        self.entrada.bind("<Return>", lambda e: self._enviar())
        btn = tk.Button(
            pie, text="Preguntar", command=self._enviar, relief="flat", bd=0,
            bg=st.ACENTO, fg="#ffffff", activebackground=st.ACENTO_OSCURO,
            activeforeground="#ffffff", font=(st.FUENTE, 10, "bold"),
            padx=14, pady=7, cursor="hand2")
        btn.pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------- acciones
    def _rueda_chat(self, evento):
        delta = int(-evento.delta / 120)
        if delta:
            self.chat.yview_scroll(delta, "units")
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

    def _escribir(self, texto, etiqueta="sistema"):
        """Agrega texto al chat (con **negritas** y *cursivas*)."""
        self.chat.config(state="normal")
        for parte in _PARTES.split(texto):
            if not parte:
                continue
            if parte.startswith("**") and parte.endswith("**") and len(parte) > 4:
                self.chat.insert("end", parte[2:-2], (etiqueta, "negrita"))
            elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
                self.chat.insert("end", parte[1:-1], (etiqueta, "cursiva"))
            else:
                self.chat.insert("end", parte, etiqueta)
        self.chat.insert("end", "\n")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _salto(self):
        """Separador visual entre mensajes."""
        self.chat.config(state="normal")
        self.chat.insert("end", "\n")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _bienvenida(self):
        self._escribir("¡Hola! Soy el soporte del sistema.", "titulo")
        self._escribir(
            "Preguntame **cómo usar el programa**: caja, ventas, permisos, "
            "Excel, respaldos y demás. Respondo con la documentación real "
            "del sistema, así que no invento nada y ando **las 24 horas**.",
            "respuesta")
        self._escribir(
            "Tocá una pregunta rápida arriba o escribí la tuya ahí abajo.",
            "fuente")

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
        self._escribir(texto, "pregunta")

        r = ayuda.resolver(texto)

        if r["ok"]:
            tema = r["tema"]
            self._escribir(tema["titulo"], "titulo")
            for parrafo in tema["parrafos"]:
                self._escribir(parrafo, "respuesta")
            if tema["id"] != "saludo":
                self._escribir(f"Fuente: {tema['seccion']}", "fuente")
            self.entrada.focus_set()
            return

        if r["ambiguas"]:
            self._escribir("Encontré más de un tema para eso", "titulo")
            self._escribir(
                "La pregunta es un poco general. Elegí cuál te sirve y "
                "tocá su botón:", "respuesta")
            for t in r["ambiguas"][:4]:
                self._escribir(f"• {t['titulo']}", "respuesta")
            self._escribir(
                "O reescribí la pregunta con un poco más de detalle.",
                "fuente")
        else:
            self._escribir("No tengo esa respuesta cargada", "titulo")
            self._escribir(
                "No encontré nada en la documentación del sistema para "
                "**" + texto + "**. Probá con otras palabras, por ejemplo "
                "«caja», «venta», «excel» o «usuarios».", "respuesta")
            extras = ayuda.alternativas(texto, 3)
            if extras:
                self._escribir(
                    "También puedo ayudarte con: "
                    + " · ".join(t["titulo"] for t in extras), "fuente")
        self.entrada.focus_set()
