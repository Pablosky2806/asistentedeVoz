"""Widget flotante para consultar y controlar el asistente local Mateo."""

import os
import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).parent
ASSISTANT_SCRIPT = BASE_DIR / "asistente_local.py"
DATA_DIR = BASE_DIR / "datos"
MEMORY_PATH = DATA_DIR / "memoria_mateo.json"
WIDGET_STATE_PATH = DATA_DIR / "estado_widget.json"
BACKGROUND = "#111316"
PANEL = "#1a1d21"
TEXT = "#f4f6f8"
MUTED = "#a1a8b0"
PURPLE = "#8a73ff"


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
        self.microphone_enabled = self._read_widget_state()

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
            self.root, bg=BACKGROUND, highlightthickness=1, highlightbackground="#2a2e34"
        )
        self.shell.pack(fill="both", expand=True)
        self.header = tk.Frame(self.shell, bg=BACKGROUND)
        self.header.pack(fill="x", padx=8, pady=6)
        self.header.bind("<ButtonPress-1>", self._start_drag)
        self.header.bind("<B1-Motion>", self._drag)

        self.icon = tk.Canvas(self.header, width=70, height=46, bg=BACKGROUND, highlightthickness=0)
        self.icon.pack(side="left", padx=(1, 8))
        self.face_outline = self.icon.create_oval(3, 3, 67, 43, fill="#30353c", outline="")
        self.icon.create_oval(5, 5, 39, 41, fill="#f3f4f6", outline="")
        self.icon.create_oval(31, 5, 65, 41, fill="#f3f4f6", outline="")
        self.icon.create_rectangle(22, 5, 48, 41, fill="#f3f4f6", outline="")
        self.eye_left = self.icon.create_oval(21, 19, 29, 27, fill="#211c20", outline="")
        self.eye_right = self.icon.create_oval(41, 19, 49, 27, fill="#211c20", outline="")
        self.mouth = self.icon.create_arc(
            29, 25, 41, 34, start=200, extent=140, style="arc", outline="#4b4146", width=2
        )
        self.pet_status = self.icon.create_oval(56, 32, 68, 44, fill="#f5a623", outline=BACKGROUND, width=2)

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
        assistant_controls = tk.Frame(controls, bg=PANEL)
        assistant_controls.pack(fill="x", pady=(0, 6))
        self.microphone_button = ttk.Button(
            assistant_controls,
            text="Pausar micrófono" if self.microphone_enabled else "Reanudar micrófono",
            style="Mateo.TButton",
            command=self.toggle_microphone,
        )
        self.microphone_button.pack(side="left")
        self.toggle_button = ttk.Button(
            assistant_controls, text="Cerrar Mateo", style="Mateo.TButton", command=self.toggle_assistant
        )
        self.toggle_button.pack(side="right")

        self.memory_status_label = tk.Label(
            controls, text="Memoria local: comprobando…", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8), anchor="w",
        )
        self.memory_status_label.pack(fill="x", pady=(2, 4))
        memory_controls = tk.Frame(controls, bg=PANEL)
        memory_controls.pack(fill="x", pady=(0, 6))
        self.memory_toggle_button = ttk.Button(
            memory_controls, text="Desactivar memoria", style="Mateo.TButton",
            command=self.toggle_memory,
        )
        self.memory_toggle_button.pack(side="left")
        ttk.Button(
            memory_controls, text="Ver archivo", style="Mateo.TButton",
            command=self.open_memory_file,
        ).pack(side="right")

        privacy_controls = tk.Frame(controls, bg=PANEL)
        privacy_controls.pack(fill="x")
        ttk.Button(
            privacy_controls, text="Borrar memoria", style="Mateo.TButton",
            command=self.clear_memory,
        ).pack(side="left")
        ttk.Button(
            privacy_controls, text="Ocultar widget", style="Mateo.TButton",
            command=self._collapse,
        ).pack(side="right")
        self._refresh_privacy_controls()

        self._bind_drag(self.header)
        self._bind_drag(self.icon)
        self._bind_drag(labels)
        for child in labels.winfo_children():
            self._bind_drag(child)

    def _read_widget_state(self) -> bool:
        try:
            state = json.loads(WIDGET_STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        return not isinstance(state, dict) or state.get("microphone_enabled", True) is not False

    def _read_memory_file(self) -> tuple[dict[str, object], bool]:
        if not MEMORY_PATH.exists():
            return {"enabled": True, "facts": []}, True
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"enabled": True, "facts": []}, False
        if not isinstance(data, dict) or not isinstance(data.get("facts", []), list):
            return {"enabled": True, "facts": []}, False
        facts = [fact for fact in data.get("facts", []) if isinstance(fact, str)]
        return {"enabled": data.get("enabled", True) is not False, "facts": facts}, True

    @staticmethod
    def _write_json_file(path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def _refresh_privacy_controls(self, schedule_next: bool = True) -> None:
        if not self.root.winfo_exists():
            return
        self.microphone_enabled = self._read_widget_state()
        self.microphone_button.configure(
            text="Pausar micrófono" if self.microphone_enabled else "Reanudar micrófono"
        )
        memory, valid = self._read_memory_file()
        if valid:
            enabled = memory.get("enabled") is not False
            facts = memory.get("facts", [])
            count = len(facts) if isinstance(facts, list) else 0
            self.memory_status_label.configure(
                text=f"Memoria local: {'activada' if enabled else 'desactivada'} · {count} datos"
            )
            self.memory_toggle_button.configure(
                state="normal",
                text="Desactivar memoria" if enabled else "Activar memoria",
            )
        else:
            self.memory_status_label.configure(text="Memoria local: archivo no válido")
            self.memory_toggle_button.configure(state="disabled")
        if schedule_next:
            self.root.after(1000, self._refresh_privacy_controls)

    def toggle_microphone(self) -> None:
        enabled = not self._read_widget_state()
        try:
            self._write_json_file(WIDGET_STATE_PATH, {"microphone_enabled": enabled})
        except OSError as error:
            messagebox.showerror("Mateo", f"No he podido cambiar el micrófono: {error}")
            return
        self.microphone_enabled = enabled
        self.microphone_button.configure(
            text="Pausar micrófono" if enabled else "Reanudar micrófono"
        )
        if enabled:
            self._set_state("En espera", "Micrófono reanudado")
        else:
            self._set_state("Pausado", "Micrófono pausado")

    def toggle_memory(self) -> None:
        memory, valid = self._read_memory_file()
        if not valid:
            messagebox.showerror("Mateo", "El archivo de memoria no es válido. Ábrelo y corrígelo antes de cambiar el ajuste.")
            return
        memory["enabled"] = memory.get("enabled") is False
        try:
            self._write_json_file(MEMORY_PATH, memory)
        except OSError as error:
            messagebox.showerror("Mateo", f"No he podido actualizar la memoria: {error}")
            return
        enabled = memory["enabled"] is True
        messagebox.showinfo(
            "Mateo",
            "Memoria activada. Mateo leerá las notas locales en el siguiente turno."
            if enabled
            else "Memoria desactivada. Las notas se conservan, pero Mateo dejará de usarlas en el siguiente turno.",
        )
        self._refresh_privacy_controls(schedule_next=False)

    def open_memory_file(self) -> None:
        if not MEMORY_PATH.exists():
            try:
                self._write_json_file(MEMORY_PATH, {"enabled": True, "facts": []})
            except OSError as error:
                messagebox.showerror("Mateo", f"No he podido crear el archivo de memoria: {error}")
                return
        try:
            os.startfile(str(MEMORY_PATH))
        except OSError as error:
            messagebox.showerror("Mateo", f"No he podido abrir el archivo de memoria: {error}")

    def clear_memory(self) -> None:
        memory, valid = self._read_memory_file()
        if not valid:
            messagebox.showerror("Mateo", "El archivo de memoria no es válido. Ábrelo y corrígelo antes de borrarlo desde aquí.")
            return
        if not messagebox.askyesno(
            "Borrar memoria local",
            "¿Quieres borrar todos los datos guardados? Mateo actualizará su contexto en el siguiente turno.",
        ):
            return
        memory["facts"] = []
        try:
            self._write_json_file(MEMORY_PATH, memory)
        except OSError as error:
            messagebox.showerror("Mateo", f"No he podido borrar la memoria: {error}")
            return
        self._add_transcript("Privacidad", "Memoria local borrada")
        self._refresh_privacy_controls(schedule_next=False)

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._drag)

    def _position_widget(self) -> None:
        self.root.update_idletasks()
        width = 300
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        self.root.geometry(f"{width}x62+{x}+12")

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
        self.root.geometry(f"410x355+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def _collapse(self) -> None:
        self.expanded = False
        self.details.pack_forget()
        self.expand_button.configure(text="⌄")
        self.root.geometry(f"300x62+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def _set_state(self, state: str, hint: str | None = None) -> None:
        self.state = state
        self.status_label.configure(text=hint or state)

    def _add_transcript(self, speaker: str, message: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}: {message}\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _handle_output_line(self, line: str) -> None:
        if line == "MATEO_WIDGET_CLOSE":
            self.close()
            return
        if "Mateo está listo" in line:
            if self.microphone_enabled:
                self._set_state("En espera", 'Di «Oye, Mateo»')
            else:
                self._set_state("Pausado", "Micrófono pausado")
        elif line.startswith("Micrófono pausado"):
            self._set_state("Pausado", "Micrófono pausado")
        elif line.startswith("Micrófono reanudado"):
            self._set_state("En espera", 'Di «Oye, Mateo»')
        elif line.startswith("Comprobando Ollama") or line.startswith("Preparando el modelo local"):
            self._set_state("Preparando", "Preparando el modelo local…")
        elif line.startswith("Esperando a que Ollama"):
            self._set_state("Preparando", "Esperando a Ollama…")
        elif line.startswith("No encuentro el modelo local") or line.startswith("No consigo conectar con Ollama"):
            self._add_transcript("Mateo", line)
            self._set_state("Error", "Revisa Ollama y su modelo")
        elif line.startswith("Orden detectada:"):
            self._add_transcript("Acción", line.partition(":")[2].strip())
        elif line.startswith("Esperando"):
            self._set_state("En espera", 'Di «Oye, Mateo»')
        elif line.startswith("Activación detectada"):
            self._set_state("Activo", "Te escucho")
        elif line == "Te escucho...":
            self._set_state("Escuchando", "Escuchando…")
        elif line.startswith("Te oigo decir:"):
            self._set_state("En espera", 'Di «Oye, Mateo» o «Mateo, apágate»')
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
        self.toggle_button.configure(text="Cerrar Mateo")
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
                if self.state not in {"Detenido", "Error"}:
                    self._set_state("Detenido", "Pulsa el widget para iniciar Mateo")
        self.root.after(100, self._read_events)

    def _animate_icon(self) -> None:
        self.animation_step = (self.animation_step + 1) % 40
        active = self.state in {"Escuchando", "Activo", "Hablando"}
        color_by_state = {
            "En espera": "#22c55e",
            "Pausado": "#8a9099",
            "Preparando": "#f5a623",
            "Iniciando": "#f5a623",
            "Escuchando": "#22c55e",
            "Activo": "#22c55e",
            "Pensando": "#8a73ff",
            "Hablando": "#34b8e8",
            "Error": "#f04452",
            "Detenido": "#8a9099",
        }
        status_color = color_by_state.get(self.state, PURPLE)
        eye_color = status_color if active and self.animation_step < 20 else "#211c20"
        self.icon.itemconfigure(self.eye_left, fill=eye_color)
        self.icon.itemconfigure(self.eye_right, fill=eye_color)
        self.icon.itemconfigure(self.pet_status, fill=status_color)
        self.icon.itemconfigure(self.face_outline, fill="#444957" if active and self.animation_step < 20 else "#30353c")
        self.icon.itemconfigure(self.mouth, outline="#8a73ff" if self.state == "Hablando" else "#4b4146")
        self.root.after(120, self._animate_icon)

    def close(self) -> None:
        self.stop_assistant()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    MateoWidget(window)
    window.mainloop()
