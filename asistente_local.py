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
import numpy as np
from faster_whisper import WhisperModel
from piper import PiperVoice
from vosk import KaldiRecognizer, Model, SetLogLevel


SAMPLE_RATE = 16_000
MODEL_PATH = Path(__file__).parent / "modelos" / "vosk-model-small-es-0.42"
PIPER_VOICE_PATH = Path(__file__).parent / "modelos" / "piper" / "es_ES-sharvard-medium.onnx"
OLLAMA_MODEL = "qwen3:8b"
WHISPER_MODEL_SIZE = "small"
WHISPER_MODEL_PATH = Path(__file__).parent / "modelos" / "whisper"
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
OPEN_ACTIONS = (
    "abre", "abreme", "abres", "abra", "abras", "abrir", "abrirme", "abrirlo", "abrirla",
    "inicia", "iniciar",
    "lanza", "ejecuta", "arranca", "arrancar",
)
LAUNCH_TARGETS: list[tuple[str, Path]] | None = None
SPEECH_APP_HINTS = (
    "Microsoft Teams", "Teams", "Steam", "WhatsApp", "Disney Plus", "Discord",
    "Spotify", "Cursor", "Chrome", "Edge",
)
ASR_NAME_ALIASES = {
    "tims": "teams",
    "tim": "teams",
    "team": "teams",
    "microsoft tims": "microsoft teams",
    "whats app": "whatsapp",
    "whats up": "whatsapp",
    "what sap": "whatsapp",
    "guasap": "whatsapp",
    "wasap": "whatsapp",
    "watsap": "whatsapp",
    "wats app": "whatsapp",
}

SYSTEM_PROMPT = """Eres Mateo, un asistente personal conversacional en español.
Responde de forma natural, cercana y breve, normalmente en una o tres frases.
No uses emojis ni emoticonos en ninguna respuesta.
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


def remove_emojis(text: str) -> str:
    """Quita emojis y emoticonos para que tampoco aparezcan en la salida."""
    filtered = []
    for character in text:
        codepoint = ord(character)
        category = unicodedata.category(character)
        is_emoji_component = (
            category in {"So", "Sk"}
            or codepoint in {0x200D, 0xFE0E, 0xFE0F, 0x20E3}
            or 0x1F3FB <= codepoint <= 0x1F3FF
        )
        if not is_emoji_component:
            filtered.append(character)

    cleaned = "".join(filtered)
    cleaned = re.sub(r"(?i)(?<!\w)(?:[:;=8][-^']?[)(/\\DPp]|<3)(?!\w)", "", cleaned)
    cleaned = re.sub(r"\s+([,.;!?])", r"\1", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


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
        r"^(?:(?:por favor|la aplicacion|la app|el programa|el juego|la carpeta|carpeta de|de|el|la|los|las|un|una|me) )+",
        "",
        target,
    )
    target = re.sub(r"\s+(?:por favor|porfa)$", "", target).strip()
    return target


def get_launch_targets() -> list[tuple[str, Path]]:
    """Indexa accesos directos de aplicaciones y juegos del menú Inicio y escritorio."""
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
        Path(os.environ["OneDrive"]) / "Desktop" if os.environ.get("OneDrive") else None,
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

            for entry in root.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_file() and entry.suffix.lower() in {".lnk", ".url"}:
                    targets.append((normalize_text(entry.stem), entry))
        except OSError:
            continue

    LAUNCH_TARGETS = targets
    return targets


def open_requested_target(query: str, allow_similar_names: bool = False) -> tuple[str, str]:
    """Abre el acceso directo de aplicación o juego que coincide con la petición."""
    if not query:
        return "empty", "Dime el nombre de la aplicación o juego."

    normalized_query = normalize_text(query)
    candidates = get_launch_targets()
    installed_names = {name for name, _path in candidates}

    # "Teams" y "Steam" se confunden al hablar español. Confirma "Steam"
    # antes de abrirlo para no ejecutar la aplicación equivocada.
    has_teams = any("teams" in name for name in installed_names)
    has_steam = any("steam" in name for name in installed_names)
    teams_sounds_like_steam = (
        normalized_query in {"teams", "team", "tims", "tim"}
        and has_steam
        and not has_teams
    )
    steam_sounds_like_teams = normalized_query == "steam"
    if not allow_similar_names and (teams_sounds_like_steam or steam_sounds_like_teams):
        return (
            "clarify",
            "He oído Steam, pero podría ser Microsoft Teams. Di el nombre completo: "
            "Microsoft Teams o Steam.",
        )

    normalized_query = ASR_NAME_ALIASES.get(normalized_query, normalized_query)
    query_tokens = set(normalized_query.split())

    def match_score(name: str) -> float:
        if normalized_query == name:
            return 1.0
        if normalized_query in name or name in normalized_query:
            return 0.94
        name_tokens = set(name.split())
        overlap = len(query_tokens & name_tokens) / max(1, len(query_tokens))
        character_similarity = difflib.SequenceMatcher(None, normalized_query, name).ratio()
        return max(overlap * 0.9, character_similarity)

    ranked = sorted(
        ((match_score(name), name, path) for name, path in candidates if name),
        reverse=True,
    )
    if not ranked or ranked[0][0] < 0.82:
        return "missing", f"No encuentro una aplicación o juego llamado {query}."

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


def capture_text(
    model: Model,
    grammar: str | None = None,
    transcriber: WhisperModel | None = None,
) -> str:
    """Graba hasta una pausa; usa Vosk para activar y Whisper para transcribir."""
    if grammar:
        recognizer = KaldiRecognizer(model, SAMPLE_RATE, grammar)
    else:
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    audio = pyaudio.PyAudio()
    stream = None
    audio_chunks: list[bytes] = []
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
            if transcriber is not None and grammar is None:
                audio_chunks.append(audio_chunk)
            if recognizer.AcceptWaveform(audio_chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip()
                if transcriber is not None and grammar is None:
                    pcm = np.frombuffer(b"".join(audio_chunks), dtype=np.int16)
                    audio_chunks.clear()
                    if pcm.size:
                        samples = pcm.astype(np.float32) / 32_768.0
                        segments, _info = transcriber.transcribe(
                            samples,
                            language="es",
                            task="transcribe",
                            beam_size=3,
                            condition_on_previous_text=False,
                            hotwords=", ".join(
                                [
                                    *SPEECH_APP_HINTS,
                                    *sorted({name for name, _path in get_launch_targets()})[:20],
                                ]
                            ),
                        )
                        transcript = " ".join(segment.text.strip() for segment in segments).strip()
                        if transcript:
                            return transcript
                elif text:
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


def converse(
    model: Model,
    voice: PiperVoice,
    local_ai: ollama.Client,
    transcriber: WhisperModel,
) -> None:
    """Mantiene una conversación local hasta escuchar una frase de despedida."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    speak(voice, "Hola, soy Mateo. ¿En qué te puedo ayudar?")

    while True:
        print("Te escucho...")
        user_text = capture_text(model, transcriber=transcriber)
        print(f"Tú: {user_text}")

        if not user_text:
            speak(voice, "No te he entendido bien. ¿Puedes repetirlo, por favor?")
            continue

        if is_farewell(user_text):
            farewell = "De acuerdo. Cuando me necesites, di Oye, Mateo."
            print(f"Mateo: {farewell}")
            speak(voice, farewell)
            return

        app_request = requested_target(user_text)
        if app_request is not None:
            result, reply = open_requested_target(app_request)
            print(f"Mateo: {reply}")
            speak(voice, reply)
            if result == "clarify":
                choice_text = capture_text(model, transcriber=transcriber)
                print(f"Tú: {choice_text}")
                choice = normalize_text(choice_text)
                if "microsoft" in choice or "teams" in choice or "tims" in choice:
                    result, reply = open_requested_target("teams", allow_similar_names=True)
                elif "steam" in choice:
                    result, reply = open_requested_target("steam", allow_similar_names=True)
                else:
                    reply = "De acuerdo, no abriré ninguna aplicación."
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
        assistant_text = remove_emojis(assistant_text)
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
    print("Cargando reconocimiento preciso de español (Whisper)...")
    transcriber = WhisperModel(
        WHISPER_MODEL_SIZE,
        device="cpu",
        compute_type="int8",
        cpu_threads=min(8, max(2, os.cpu_count() or 4)),
        download_root=str(WHISPER_MODEL_PATH),
    )
    print("Cargando voz local de Mateo...")
    voice = PiperVoice.load(str(PIPER_VOICE_PATH))
    local_ai = ollama.Client(host="http://localhost:11434")
    print(
        f"Mateo está listo. Modelos locales: {OLLAMA_MODEL} y Whisper {WHISPER_MODEL_SIZE}. "
        "Pulsa Ctrl+C para salir."
    )

    try:
        while True:
            wait_for_wake_word(speech_model)
            converse(speech_model, voice, local_ai, transcriber)
    except KeyboardInterrupt:
        print("\nAsistente cerrado.")


if __name__ == "__main__":
    main()
