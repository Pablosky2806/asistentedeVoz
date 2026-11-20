# Asistente de voz con ElevenLabs

Proyecto en Python para mantener conversaciones por voz.

## Arquitectura

La primera versión usa **ElevenAgents** mediante el SDK oficial de Python. ElevenLabs proporciona el agente conversacional y gestiona la entrada de voz, las transcripciones y el audio de respuesta. El SDK conecta el micrófono y los altavoces del equipo con una sesión del agente.

El programa inicia una conversación cuando lo ejecutas y la mantiene hasta que termina el agente o pulsas `Ctrl+C`. No incluye una palabra de activación permanente (por ejemplo, «Oye asistente»); eso se puede añadir en una fase posterior.

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

4. Copia la plantilla si todavía no existe `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Añade tu API key de ElevenLabs en `ELEVENLABS_API_KEY` dentro de `.env`. La clave se queda en tu equipo y no se sube a GitHub.

## Crear y ejecutar el agente

1. Crea el agente privado en ElevenLabs. El script configura un agente en español con un saludo y un prompt inicial.
2. Ejecuta una sola vez:

   ```powershell
   python crear_agente.py
   ```

   El script crea el agente mediante la API y escribe su `AGENT_ID` en `.env`. Si ya hay un ID configurado, se detiene para evitar crear duplicados.

3. Asegúrate de que Windows tiene micrófono y altavoces configurados y ejecuta:

   ```powershell
   python asistente.py
   ```

4. Habla con el asistente; pulsa `Ctrl+C` para cerrar la sesión.

Consulta la [guía oficial de agentes](https://elevenlabs.io/docs/eleven-agents/quickstart) y la [API oficial para crear agentes](https://elevenlabs.io/docs/api-reference/agents/create).

## Seguimiento del proyecto

- `main`: base estable.
- `feature/elevenagents-architecture`: arquitectura y configuración inicial.
- `feature/voice-session`: primera sesión de conversación.
- `feature/agent-config`: validación de la configuración local.
- `feature/agent-setup-script`: creación local del agente por API.

Los avances se registran en commits pequeños, explicados por fase.
