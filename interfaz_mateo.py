"""Ventana ligera para controlar y ver el estado del asistente local Mateo."""

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
BACKGROUND = "#101018"
PANEL = "#191923"
TEXT = "#f5f3ff"
MUTED = "#aaa6bb"
PURPLE = "#b388ff"


class MateoWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mateo · Asistente de voz")
        self.root.geometry("440x650")
        self.root.minsize(400, 600)
        self.root.configure(bg=BACKGROUND)

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.state = "Preparado"
        self.animation_step = 0

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._read_events)
        self.root.after(350, self.start_assistant)
        self._animate_logo()

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND)
        header.pack(fill="x", padx=28, pady=(22, 10))

        tk.Label(
            header, text="MATEO", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header, text="ASISTENTE PERSONAL LOCAL", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        self.canvas = tk.Canvas(
            self.root, width=300, height=280, bg=BACKGROUND,
            highlightthickness=0,
        )
        self.canvas.pack(pady=(12, 2))
        self.orb = self.canvas.create_oval(75, 35, 225, 185, fill="#5a398e", outline="")
        self.canvas.create_oval(88, 48, 212, 172, fill="#9d6ce0", outline="")
        self.canvas.create_oval(104, 64, 196, 156, fill="#c7a3ff", outline="")
        self.canvas.create_oval(119, 74, 157, 106, fill="#e9d9ff", outline="")
        self.canvas.create_text(
            150, 120, text="M", fill="#34214f", font=("Segoe UI", 48, "bold")
        )

        self.status_label = tk.Label(
            self.root, text="Preparado", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 17, "bold"),
        )
        self.status_label.pack(pady=(0, 4))
        self.hint_label = tk.Label(
            self.root, text='Di «Oye, Mateo» para empezar a hablar.',
            bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 10),
        )
        self.hint_label.pack(pady=(0, 16))

        transcript_panel = tk.Frame(self.root, bg=PANEL, highlightthickness=1, highlightbackground="#302b3d")
        transcript_panel.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        tk.Label(
            transcript_panel, text="CONVERSACIÓN", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 6))
        self.transcript = tk.Text(
            transcript_panel, bg=PANEL, fg=TEXT, insertbackground=TEXT,
            font=("Segoe UI", 10), wrap="word", relief="flat", borderwidth=0,
            state="disabled", padx=16, pady=4,
        )
        self.transcript.pack(fill="both", expand=True, padx=0, pady=(0, 12))

        controls = tk.Frame(self.root, bg=BACKGROUND)
        controls.pack(fill="x", padx=24, pady=(0, 22))
        self.toggle_button = ttk.Button(controls, text="Detener Mateo", command=self.toggle_assistant)
        self.toggle_button.pack(side="left", fill="x", expand=True, ipady=7)
        ttk.Button(controls, text="Cerrar ventana", command=self.close).pack(
            side="left", padx=(10, 0), ipady=7
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TButton", background="#302541", foreground=TEXT,
            bordercolor="#45345f", padding=(12, 8), font=("Segoe UI", 10, "bold"),
        )
        style.map("TButton", background=[("active", "#493664")])

    def _set_state(self, state: str, hint: str | None = None) -> None:
        self.state = state
        self.status_label.configure(text=state)
        if hint:
            self.hint_label.configure(text=hint)

    def _add_transcript(self, speaker: str, message: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n{message}\n\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _handle_output_line(self, line: str) -> None:
        if "Mateo está listo" in line:
            self._set_state("En espera", 'Di «Oye, Mateo» para empezar a hablar.')
        elif line.startswith("Esperando"):
            self._set_state("En espera", 'Di «Oye, Mateo» para empezar a hablar.')
        elif line.startswith("Activación detectada"):
            self._set_state("Activo", "Te escucho.")
        elif line == "Te escucho...":
            self._set_state("Escuchando", "Habla con naturalidad.")
        elif line.startswith("Tú:"):
            self._add_transcript("Tú", line.partition(":")[2].strip())
            self._set_state("Pensando", "Estoy preparando una respuesta.")
        elif line.startswith("Mateo:"):
            self._add_transcript("Mateo", line.partition(":")[2].strip())
            self._set_state("Hablando", "Mateo está respondiendo.")

    def start_assistant(self) -> None:
        if self.process and self.process.poll() is None:
            return
        if not ASSISTANT_SCRIPT.is_file():
            self._set_state("No encuentro a Mateo", "Falta asistente_local.py en la carpeta del proyecto.")
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
            self._set_state("No se pudo iniciar", str(error))
            return

        self.toggle_button.configure(text="Detener Mateo")
        self._set_state("Iniciando", "Cargando el reconocimiento y la voz local.")
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
        self._set_state("Detenido", "Pulsa «Iniciar Mateo» cuando quieras volver a usarlo.")

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
                    self._set_state("Mateo se ha detenido", "Pulsa «Iniciar Mateo» para volver a empezar.")
        self.root.after(100, self._read_events)

    def _animate_logo(self) -> None:
        self.animation_step = (self.animation_step + 1) % 60
        pulse = abs(30 - self.animation_step) / 30
        inset = int(pulse * 8)
        self.canvas.coords(self.orb, 67 - inset, 27 - inset, 233 + inset, 193 + inset)
        if self.state in {"Escuchando", "Activo"}:
            color = "#d5baff"
        elif self.state in {"Hablando", "Pensando"}:
            color = "#bb8aff"
        else:
            color = "#8f62c8"
        self.canvas.itemconfigure(self.orb, fill=color)
        self.root.after(60, self._animate_logo)

    def close(self) -> None:
        self.stop_assistant()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    MateoWindow(window)
    window.mainloop()
