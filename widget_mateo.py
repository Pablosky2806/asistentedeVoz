"""Widget flotante para consultar y controlar el asistente local Mateo."""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk


BASE_DIR = Path(__file__).parent
ASSISTANT_SCRIPT = BASE_DIR / "asistente_local.py"
BACKGROUND = "#17131f"
PANEL = "#211b2b"
TEXT = "#f7f2ff"
MUTED = "#b9adca"
PURPLE = "#bb8aff"


class MateoWidget:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BACKGROUND)
        self.root.title("Mateo")

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.state = "Iniciando"
        self.expanded = False
        self.animation_step = 0
        self.drag_offset = (0, 0)

        self._build_widget()
        self._position_widget()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _event: self._collapse())
        self.root.after(100, self._read_events)
        self.root.after(350, self.start_assistant)
        self._animate_icon()

    def _build_widget(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Mateo.TButton", background="#382a4b", foreground=TEXT,
            bordercolor="#514064", padding=(10, 5), font=("Segoe UI", 9, "bold"),
        )
        style.map("Mateo.TButton", background=[("active", "#513d6b")])

        self.shell = tk.Frame(
            self.root, bg=BACKGROUND, highlightthickness=1, highlightbackground="#4a3c5a"
        )
        self.shell.pack(fill="both", expand=True)
        self.header = tk.Frame(self.shell, bg=BACKGROUND)
        self.header.pack(fill="x", padx=8, pady=6)
        self.header.bind("<ButtonPress-1>", self._start_drag)
        self.header.bind("<B1-Motion>", self._drag)

        self.icon = tk.Canvas(self.header, width=42, height=42, bg=BACKGROUND, highlightthickness=0)
        self.icon.pack(side="left", padx=(2, 7))
        self.icon.create_oval(4, 4, 38, 38, fill="#563878", outline="")
        self.icon.create_oval(8, 8, 34, 34, fill=PURPLE, outline="")
        self.icon.create_text(21, 21, text="M", fill="#30213e", font=("Segoe UI", 16, "bold"))

        labels = tk.Frame(self.header, bg=BACKGROUND)
        labels.pack(side="left", fill="x", expand=True)
        tk.Label(
            labels, text="Mateo", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 11, "bold"), anchor="w",
        ).pack(anchor="w")
        self.status_label = tk.Label(
            labels, text="Iniciando…", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 8), anchor="w",
        )
        self.status_label.pack(anchor="w")

        self.expand_button = tk.Button(
            self.header, text="⌄", command=self._toggle_expanded,
            bg=BACKGROUND, fg=MUTED, activebackground=PANEL, activeforeground=TEXT,
            relief="flat", borderwidth=0, font=("Segoe UI", 13, "bold"), cursor="hand2",
        )
        self.expand_button.pack(side="right", padx=(4, 2))
        self.close_button = tk.Button(
            self.header, text="×", command=self.close,
            bg=BACKGROUND, fg=MUTED, activebackground=PANEL, activeforeground=TEXT,
            relief="flat", borderwidth=0, font=("Segoe UI", 13), cursor="hand2",
        )
        self.close_button.pack(side="right")

        self.details = tk.Frame(self.shell, bg=PANEL)
        tk.Label(
            self.details, text="ACTIVIDAD RECIENTE", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8, "bold"), anchor="w",
        ).pack(fill="x", padx=11, pady=(9, 4))
        self.transcript = tk.Text(
            self.details, height=5, bg=PANEL, fg=TEXT, insertbackground=TEXT,
            font=("Segoe UI", 9), wrap="word", relief="flat", borderwidth=0,
            state="disabled", padx=10, pady=3,
        )
        self.transcript.pack(fill="both", expand=True, padx=2)
        controls = tk.Frame(self.details, bg=PANEL)
        controls.pack(fill="x", padx=9, pady=8)
        self.toggle_button = ttk.Button(
            controls, text="Detener Mateo", style="Mateo.TButton", command=self.toggle_assistant
        )
        self.toggle_button.pack(side="left")
        ttk.Button(
            controls, text="Ocultar widget", style="Mateo.TButton", command=self._collapse
        ).pack(side="right")

        self._bind_drag(self.header)
        self._bind_drag(self.icon)
        self._bind_drag(labels)
        for child in labels.winfo_children():
            self._bind_drag(child)

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._drag)

    def _position_widget(self) -> None:
        self.root.update_idletasks()
        width = 250
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        self.root.geometry(f"{width}x58+{x}+12")

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        x = event.x_root - self.drag_offset[0]
        y = max(0, event.y_root - self.drag_offset[1])
        self.root.geometry(f"+{x}+{y}")

    def _toggle_expanded(self) -> None:
        if self.expanded:
            self._collapse()
            return
        self.expanded = True
        self.details.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.expand_button.configure(text="⌃")
        self.root.geometry(f"360x270+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def _collapse(self) -> None:
        self.expanded = False
        self.details.pack_forget()
        self.expand_button.configure(text="⌄")
        self.root.geometry(f"250x58+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def _set_state(self, state: str, hint: str | None = None) -> None:
        self.state = state
        self.status_label.configure(text=hint or state)

    def _add_transcript(self, speaker: str, message: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}: {message}\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _handle_output_line(self, line: str) -> None:
        if "Mateo está listo" in line:
            self._set_state("En espera", 'Di «Oye, Mateo»')
        elif line.startswith("Esperando"):
            self._set_state("En espera", 'Di «Oye, Mateo»')
        elif line.startswith("Activación detectada"):
            self._set_state("Activo", "Te escucho")
        elif line == "Te escucho...":
            self._set_state("Escuchando", "Escuchando…")
        elif line.startswith("Tú:"):
            self._add_transcript("Tú", line.partition(":")[2].strip())
            self._set_state("Pensando", "Pensando…")
        elif line.startswith("Mateo:"):
            self._add_transcript("Mateo", line.partition(":")[2].strip())
            self._set_state("Hablando", "Respondiendo…")

    def start_assistant(self) -> None:
        if self.process and self.process.poll() is None:
            return
        if not ASSISTANT_SCRIPT.is_file():
            self._set_state("Error", "No encuentro asistente_local.py")
            return
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", str(ASSISTANT_SCRIPT)],
                cwd=BASE_DIR,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as error:
            self._set_state("Error", str(error))
            return
        self.toggle_button.configure(text="Detener Mateo")
        self._set_state("Iniciando", "Cargando…")
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _read_process_output(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self.events.put(("output", line.rstrip()))
        self.events.put(("exit", str(process.poll())))

    def stop_assistant(self) -> None:
        process = self.process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        self.process = None
        self.toggle_button.configure(text="Iniciar Mateo")
        self._set_state("Detenido", "Mateo está detenido")

    def toggle_assistant(self) -> None:
        if self.process and self.process.poll() is None:
            self.stop_assistant()
        else:
            self.start_assistant()

    def _read_events(self) -> None:
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "output":
                self._handle_output_line(value)
            elif event == "exit" and self.process is not None:
                self.process = None
                self.toggle_button.configure(text="Iniciar Mateo")
                if self.state != "Detenido":
                    self._set_state("Detenido", "Pulsa el widget para iniciar Mateo")
        self.root.after(100, self._read_events)

    def _animate_icon(self) -> None:
        self.animation_step = (self.animation_step + 1) % 40
        bright = self.state in {"Escuchando", "Activo", "Hablando"}
        color = "#d5baff" if bright and self.animation_step < 20 else PURPLE
        self.icon.itemconfigure(2, fill=color)
        self.root.after(120, self._animate_icon)

    def close(self) -> None:
        self.stop_assistant()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    MateoWidget(window)
    window.mainloop()
