"""Asistente de voz con activación local por frase y ElevenAgents."""

import json
import os
import unicodedata
from pathlib import Path

import pyaudio
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
from vosk import KaldiRecognizer, Model, SetLogLevel


SAMPLE_RATE = 16_000
WAKE_PHRASES = ("oye mateo", "illo mateo")
MODEL_PATH = Path(__file__).parent / "modelos" / "vosk-model-small-es-0.42"


def normalize_text(text: str) -> str:
    """Normaliza el texto reconocido para comparar las frases de activación."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )
    cleaned = "".join(
        character if character.isalnum() else " " for character in without_accents
    )
    return " ".join(cleaned.split())


def wait_for_wake_word(model: Model) -> None:
    """Escucha el micrófono localmente hasta reconocer una frase de activación."""
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
        print('Esperando "Oye, Mateo" o "Illo, Mateo"...')
        last_displayed_text = ""

        while True:
            audio_chunk = stream.read(4_000, exception_on_overflow=False)
            if recognizer.AcceptWaveform(audio_chunk):
                result = json.loads(recognizer.Result())
                recognized_text = result.get("text", "")
            else:
                result = json.loads(recognizer.PartialResult())
                recognized_text = result.get("partial", "")

            normalized = normalize_text(recognized_text)
            if normalized and normalized != last_displayed_text:
                print(f"Te oigo decir: {recognized_text}")
            last_displayed_text = normalized

            if any(phrase in normalized for phrase in WAKE_PHRASES):
                print("Activación detectada. Conectando con Mateo...")
                return
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        audio.terminate()


def create_conversation(
    client: ElevenLabs, agent_id: str, requires_auth: bool
) -> Conversation:
    """Prepara una sesión de voz con el agente de ElevenLabs."""
    return Conversation(
        client,
        agent_id,
        requires_auth=requires_auth,
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=lambda response: print(f"Mateo: {response}"),
        callback_agent_response_correction=lambda original, corrected: print(
            f"Mateo (corregido): {original} -> {corrected}"
        ),
        callback_user_transcript=lambda transcript: print(f"Tú: {transcript}"),
    )


def main() -> None:
    load_dotenv()

    agent_id = (os.getenv("AGENT_ID") or "").strip()
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip() or None

    if not agent_id or agent_id == "your-agent-id":
        raise SystemExit("Falta AGENT_ID. Añade el ID de tu agente al archivo .env.")
    if not MODEL_PATH.is_dir():
        raise SystemExit(
            "No encuentro el modelo de Vosk. Comprueba que está en "
            f'"{MODEL_PATH}".'
        )

    SetLogLevel(-1)
    model = Model(str(MODEL_PATH))
    client = ElevenLabs(api_key=api_key)
    print("Mateo está listo. Pulsa Ctrl+C para salir.")

    conversation = None
    try:
        while True:
            wait_for_wake_word(model)
            conversation = create_conversation(
                client, agent_id, requires_auth=api_key is not None
            )
            conversation.start_session()
            conversation_id = conversation.wait_for_session_end()
            print(f"Conversación finalizada: {conversation_id}")
            conversation = None
    except KeyboardInterrupt:
        if conversation is not None:
            conversation.end_session()
        print("\nAsistente cerrado.")


if __name__ == "__main__":
    main()
