"""Asistente de voz basado en una sesión de ElevenAgents."""

import os

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def main() -> None:
    load_dotenv()

    agent_id = (os.getenv("AGENT_ID") or "").strip()
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip() or None

    if not agent_id or agent_id == "your-agent-id":
        raise SystemExit(
            "Falta AGENT_ID. Añade el ID de tu agente al archivo .env."
        )

    client = ElevenLabs(api_key=api_key)
    conversation = Conversation(
        client,
        agent_id,
        requires_auth=api_key is not None,
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=lambda response: print(f"Asistente: {response}"),
        callback_agent_response_correction=lambda original, corrected: print(
            f"Asistente (corregido): {original} -> {corrected}"
        ),
        callback_user_transcript=lambda transcript: print(f"Tú: {transcript}"),
    )

    print("Iniciando conversación. Habla por el micrófono; pulsa Ctrl+C para salir.")

    try:
        conversation.start_session()
        conversation_id = conversation.wait_for_session_end()
        print(f"Sesión finalizada: {conversation_id}")
    except KeyboardInterrupt:
        conversation.end_session()
        print("\nSesión cerrada.")


if __name__ == "__main__":
    main()
