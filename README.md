# Asistente de voz con ElevenLabs

Proyecto en Python para mantener conversaciones por voz.

## Arquitectura

La primera versión usa **ElevenAgents** mediante el SDK oficial de Python. ElevenLabs proporciona el agente conversacional y gestiona la entrada de voz, las transcripciones y el audio de respuesta. El SDK conecta el micrófono y los altavoces del equipo con una sesión del agente.

Debes crear y configurar un agente en ElevenLabs y obtener su `AGENT_ID`. Si el agente es privado, también necesitarás `ELEVENLABS_API_KEY`. Las credenciales se guardan localmente en `.env`, archivo que Git ignora.

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

4. Copia la plantilla de variables y complétala con los valores de ElevenLabs:

   ```powershell
   Copy-Item .env.example .env
   ```

   `AGENT_ID` es obligatorio. `ELEVENLABS_API_KEY` solo se requiere si el agente tiene autenticación habilitada.

5. Inicia el asistente:

   ```powershell
   python asistente.py
   ```

Asegúrate de que Windows tiene un micrófono y unos altavoces configurados. No subas `.env` ni compartas la API key.

## Seguimiento del proyecto

- `main`: rama estable.
- `feature/elevenagents-architecture`: arquitectura y configuración inicial.
- `feature/voice-session`: primera sesión de conversación.

Los avances se registran en commits pequeños, explicados por fase.
