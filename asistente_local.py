"""Asistente local: Vosk para voz, Ollama para respuestas y Piper para audio."""

import io
import json
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
END_PHRASES = ("adios mateo", "terminar conversacion", "cerrar conversacion")

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

        if any(phrase in normalize_text(user_text) for phrase in END_PHRASES):
            farewell = "De acuerdo. Cuando me necesites, di Oye, Mateo."
            print(f"Mateo: {farewell}")
            speak(voice, farewell)
            return

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
