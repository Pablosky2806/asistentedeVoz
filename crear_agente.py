"""Crea una vez el agente privado de ElevenLabs y guarda su ID localmente."""

import os
from pathlib import Path

from dotenv import load_dotenv, set_key
from elevenlabs import ElevenLabs
from elevenlabs.types import (
    AgentConfig,
    AgentPlatformSettingsRequestModel,
    AuthSettings,
    ConversationalConfig,
    PromptAgentApiModelOutput,
)

ENV_FILE = Path(".env")


def main() -> None:
    load_dotenv(ENV_FILE)

    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    agent_id = (os.getenv("AGENT_ID") or "").strip()

    if not api_key or api_key == "your-api-key":
        raise SystemExit(
            "Falta ELEVENLABS_API_KEY en .env. Añádela localmente y vuelve a intentarlo."
        )

    if agent_id and agent_id != "your-agent-id":
        raise SystemExit(
            "Ya hay un AGENT_ID configurado. No crearé otro agente para evitar duplicados."
        )

    client = ElevenLabs(api_key=api_key)
    result = client.conversational_ai.agents.create(
        name="Asistente de voz",
        conversation_config=ConversationalConfig(
            agent=AgentConfig(
                first_message="Hola, soy tu asistente de voz. ¿En qué puedo ayudarte?",
                language="es",
                prompt=PromptAgentApiModelOutput(
                    prompt=(
                        "Eres un asistente personal de voz en español. "
                        "Responde de forma clara, breve y natural. Mantén el contexto "
                        "de la conversación. No inventes datos: si no sabes algo o te "
                        "falta información, dilo y pregunta para aclararlo."
                    )
                ),
            )
        ),
        platform_settings=AgentPlatformSettingsRequestModel(
            auth=AuthSettings(enable_auth=True)
        ),
    )

    set_key(str(ENV_FILE), "AGENT_ID", result.agent_id)
    print(f"Agente creado y guardado en .env. AGENT_ID={result.agent_id}")
    print("Ya puedes iniciar la conversación con: python asistente.py")


if __name__ == "__main__":
    main()
