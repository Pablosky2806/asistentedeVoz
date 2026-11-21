"""Asistente local: Vosk para voz, Ollama para respuestas y Piper para audio."""

import io
import json
import difflib
import os
import re
import unicodedata
import wave
from pathlib import Path

import ollama
import pyaudio
from piper import PiperVoice
from vosk import KaldiRecognizer, Model, SetLogLevel


SAMPLE_RATE = 16_000
MODEL_PATH = Path(__file__).parent / "modelos" / "vosk-model-small-es-0.42"
PIPER_VOICE_PATH = Path(__file__).parent / "modelos" / "piper" / "es_ES-davefx-medium.onnx"
OLLAMA_MODEL = "qwen3:8b"
WAKE_PHRASES = ("oye mateo", "illo mateo", "y yo mateo")
WAKE_GRAMMAR = json.dumps([*WAKE_PHRASES, "[unk]"], ensure_ascii=False)
END_PHRASES = (
    "adios",
    "hasta luego",
    "hasta pronto",
    "me voy",
    "eso es todo",
    "no necesito nada mas",
    "ya no te necesito",
    "puedes descansar",
    "deja de escuchar",
    "para de escuchar",
    "terminar conversacion",
    "cerrar conversacion",
    "quiero terminar",
    "hemos terminado",
    "terminamos",
)
OPEN_ACTIONS = ("abre", "abres", "abrir", "inicia", "iniciar", "lanza", "ejecuta")
LAUNCH_TARGETS: list[tuple[str, Path]] | None = None

SYSTEM_PROMPT = """Eres Mateo, un asistente personal conversacional en español.
Responde de forma natural, cercana y breve, normalmente en una o tres frases.
Recuerda el contexto de esta conversación mientras siga abierta. No inventes
datos; si no sabes algo, dilo con claridad. No des consejos médicos, legales
ni financieros profesionales."""


def normalize_text(text: str) -> str:
    """Normaliza el texto reconocido para comparar frases."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )
    cleaned = "".join(
        character if character.isalnum() else " " for character in without_accents
    )
    return " ".join(cleaned.split())


def is_farewell(text: str) -> bool:
    """Detecta despedidas habituales sin exigir una frase exacta."""
    normalized = f" {normalize_text(text)} "
    return any(f" {phrase} " in normalized for phrase in END_PHRASES)


def requested_target(text: str) -> str | None:
    """Extrae el nombre de una aplicación o carpeta de una orden de apertura."""
    normalized = normalize_text(text)
    action_pattern = r"\b(?:" + "|".join(OPEN_ACTIONS) + r")\b"
    match = re.search(action_pattern + r"\s+(.+)$", normalized)
    if not match:
        return None
    target = match.group(1)
    target = re.sub(
        r"^(?:(?:por favor|la aplicacion|la app|el programa|el juego|la carpeta|carpeta de|de|el|la|los|las|un|una) )+",
        "",
        target,
    )
    target = re.sub(r"\s+(?:por favor|porfa)$", "", target).strip()
    return target


def get_launch_targets() -> list[tuple[str, Path]]:
    """Indexa accesos directos y carpetas habituales del usuario una vez."""
    global LAUNCH_TARGETS
    if LAUNCH_TARGETS is not None:
        return LAUNCH_TARGETS

    appdata = Path(os.environ.get("APPDATA", ""))
    programdata = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
    home = Path.home()
    roots = {
        appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        programdata / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        Path(os.environ["OneDrive"]) if os.environ.get("OneDrive") else None,
        Path(os.environ["OneDriveCommercial"]) if os.environ.get("OneDriveCommercial") else None,
    }
    targets: list[tuple[str, Path]] = []

    for root in (path for path in roots if path and path.is_dir()):
        is_start_menu = "Start Menu" in str(root)
        try:
            if is_start_menu:
                for shortcut in root.rglob("*"):
                    if shortcut.is_file() and shortcut.suffix.lower() in {".lnk", ".url"}:
                        targets.append((normalize_text(shortcut.stem), shortcut))
                continue

            depth_limit = 2 if root.name.lower() != "desktop" else 0
            for entry in root.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_file() and entry.suffix.lower() in {".lnk", ".url"}:
                    targets.append((normalize_text(entry.stem), entry))
                elif entry.is_dir():
                    targets.append((normalize_text(entry.name), entry))
                    if depth_limit:
                        for child in entry.iterdir():
                            if child.is_dir() and not child.name.startswith("."):
                                targets.append((normalize_text(child.name), child))
        except OSError:
            continue

    LAUNCH_TARGETS = targets
    return targets


def open_requested_target(query: str) -> tuple[str, str]:
    """Abre el mejor acceso directo o carpeta que coincide con la petición."""
    if not query:
        return "empty", "Dime el nombre de la aplicación, juego o carpeta."

    normalized_query = normalize_text(query)
    candidates = get_launch_targets()
    ranked = sorted(
        (
            (difflib.SequenceMatcher(None, normalized_query, name).ratio(), name, path)
            for name, path in candidates
            if name
        ),
        reverse=True,
    )
    if not ranked or ranked[0][0] < 0.68:
        return "missing", f"No encuentro un acceso directo o carpeta llamado {query}."

    best_score, best_name, best_path = ranked[0]
    if (
        len(ranked) > 1
        and best_name != ranked[1][1]
        and best_score - ranked[1][0] < 0.08
    ):
        options = " o ".join(item[1] for item in ranked[:2])
        return "ambiguous", f"He encontrado varias coincidencias: {options}. ¿Cuál quieres?"

    try:
        os.startfile(str(best_path))
    except OSError:
        return "error", f"He encontrado {best_name}, pero Windows no pudo abrirlo."
    return "opened", f"Abriendo {best_name}."


def capture_text(model: Model, grammar: str | None = None) -> str:
    """Escucha hasta que Vosk cierre una frase tras una pausa."""
    if grammar:
        recognizer = KaldiRecognizer(model, SAMPLE_RATE, grammar)
    else:
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    audio = pyaudio.PyAudio()
    stream = None
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=4_000,
        )
        stream.start_stream()
        while True:
            audio_chunk = stream.read(4_000, exception_on_overflow=False)
            if recognizer.AcceptWaveform(audio_chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip()
                if text:
                    return text
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        audio.terminate()


def wait_for_wake_word(model: Model) -> None:
    """Espera localmente una de las frases de activación."""
    print('Esperando "Oye, Mateo" o "Illo, Mateo"...')
    while True:
        text = capture_text(model, WAKE_GRAMMAR)
        normalized = normalize_text(text)
        print(f"Te oigo decir: {text}")
        if any(phrase in normalized for phrase in WAKE_PHRASES):
            print("Activación detectada. Mateo te escucha.")
            return


def speak(voice: PiperVoice, text: str) -> None:
    """Genera y reproduce audio localmente con Piper."""
    audio_buffer = io.BytesIO()
    with wave.open(audio_buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    audio_buffer.seek(0)

    audio = pyaudio.PyAudio()
    stream = None
    try:
        with wave.open(audio_buffer, "rb") as wav_file:
            stream = audio.open(
                format=audio.get_format_from_width(wav_file.getsampwidth()),
                channels=wav_file.getnchannels(),
                rate=wav_file.getframerate(),
                output=True,
            )
            audio_chunk = wav_file.readframes(2_048)
            while audio_chunk:
                stream.write(audio_chunk)
                audio_chunk = wav_file.readframes(2_048)
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        audio.terminate()


def converse(model: Model, voice: PiperVoice, local_ai: ollama.Client) -> None:
    """Mantiene una conversación local hasta escuchar una frase de despedida."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    speak(voice, "Hola, soy Mateo. ¿En qué te puedo ayudar?")

    while True:
        print("Te escucho...")
        user_text = capture_text(model)
        print(f"Tú: {user_text}")

        if is_farewell(user_text):
            farewell = "De acuerdo. Cuando me necesites, di Oye, Mateo."
            print(f"Mateo: {farewell}")
            speak(voice, farewell)
            return

        app_request = requested_target(user_text)
        if app_request is not None:
            _, reply = open_requested_target(app_request)
            print(f"Mateo: {reply}")
            speak(voice, reply)
            continue

        messages.append({"role": "user", "content": user_text})
        try:
            response = local_ai.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                options={"temperature": 0.7, "num_ctx": 4_096},
            )
        except Exception as error:
            print(f"No puedo conectar con el modelo local de Ollama: {error}")
            speak(voice, "Ahora mismo no puedo conectar con mi modelo local.")
            return

        assistant_text = response.message.content.strip()
        if not assistant_text:
            assistant_text = "No he podido preparar una respuesta. ¿Puedes repetirlo?"
        print(f"Mateo: {assistant_text}")
        messages.append({"role": "assistant", "content": assistant_text})

        # Limita el historial temporal para que la conversación no crezca sin límite.
        if len(messages) > 13:
            messages = [messages[0], *messages[-12:]]
        speak(voice, assistant_text)


def main() -> None:
    if not MODEL_PATH.is_dir():
        raise SystemExit(f"No encuentro el modelo español de Vosk en: {MODEL_PATH}")
    if not PIPER_VOICE_PATH.is_file():
        raise SystemExit(
            "No encuentro la voz local de Piper. Descárgala con las instrucciones "
            "del README."
        )

    SetLogLevel(-1)
    print("Cargando reconocimiento de voz español...")
    speech_model = Model(str(MODEL_PATH))
    print("Cargando voz local de Mateo...")
    voice = PiperVoice.load(str(PIPER_VOICE_PATH))
    local_ai = ollama.Client(host="http://localhost:11434")
    print(f"Mateo está listo. Modelo local: {OLLAMA_MODEL}. Pulsa Ctrl+C para salir.")

    try:
        while True:
            wait_for_wake_word(speech_model)
            converse(speech_model, voice, local_ai)
    except KeyboardInterrupt:
        print("\nAsistente cerrado.")


if __name__ == "__main__":
    main()
