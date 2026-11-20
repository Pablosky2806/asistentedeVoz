# Asistente de voz con ElevenLabs

Proyecto en Python para mantener conversaciones por voz.

## Arquitectura

La primera versión usa **ElevenAgents** mediante el SDK oficial de Python. ElevenLabs proporciona el agente conversacional y gestiona la entrada de voz, las transcripciones y el audio de respuesta. El SDK conecta el micrófono y los altavoces del equipo con una sesión del agente.

El programa inicia una conversación cuando lo ejecutas y la mantiene hasta que termina el agente o pulsas `Ctrl+C`. No incluye una palabra de activación permanente (por ejemplo, «Oye asistente»); eso se puede añadir en una fase posterior.

## Crear el agente en ElevenLabs

1. Entra en el panel de ElevenLabs y crea un agente nuevo con la plantilla vacía.
2. En la pestaña del agente, configura el saludo y el comportamiento. Puedes empezar con este prompt y modificarlo a tu gusto:

   > Eres un asistente de voz en español. Responde de forma clara, breve y natural. Si no sabes algo o te falta información, dilo y pregunta para aclararlo.

3. En la pestaña de voz, selecciona una voz y prueba el agente con el botón de prueba.
4. Copia el ID del agente desde el panel de ElevenLabs.
5. Pega ese ID en `AGENT_ID` en el archivo `.env` local. Si el agente requiere autenticación, añade también tu API key en `ELEVENLABS_API_KEY`.

La clave y el archivo `.env` se quedan en tu equipo; Git ignora `.env`. Para crear y probar un agente, consulta la [guía oficial de ElevenLabs](https://elevenlabs.io/docs/eleven-agents/quickstart).

## Preparación en Windows

1. Instala Python 3.10 o posterior.
2. Crea y activa un entorno virtual:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Si todavía no existe `.env`, crea una copia de la plantilla:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Inicia el asistente:

   ```powershell
   python asistente.py
   ```

Asegúrate de que Windows tiene un micrófono y unos altavoces configurados. `AGENT_ID` es obligatorio. `ELEVENLABS_API_KEY` solo se requiere si el agente tiene autenticación habilitada.

## Seguimiento del proyecto

- `main`: base estable.
- `feature/elevenagents-architecture`: arquitectura y configuración inicial.
- `feature/voice-session`: primera sesión de conversación.
- `feature/agent-config`: validación de la configuración local.

Los avances se registran en commits pequeños, explicados por fase.
