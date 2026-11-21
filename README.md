# Asistente de voz con ElevenLabs

Proyecto en Python para mantener conversaciones por voz con Mateo, un agente de ElevenLabs.

## Cómo funciona

Vosk escucha el micrófono localmente y espera una de estas frases: **«Oye, Mateo»** o **«Illo, Mateo»**. Cuando detecta una, inicia una conversación de voz con ElevenLabs. Al terminar la conversación, vuelve a esperar la frase. Pulsa `Ctrl+C` para cerrar el programa.

El audio de espera se procesa en el equipo con el modelo español de Vosk. ElevenLabs recibe audio cuando comienza la conversación con Mateo.

## Preparación en Windows

Se recomienda Python 3.13 en Windows para instalar PyAudio sin compilarlo manualmente.

1. Crea y activa un entorno virtual:

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Descarga el modelo pequeño de español desde [Vosk Models](https://alphacephei.com/vosk/models) (`vosk-model-small-es-0.42`, aproximadamente 39 MB). Extrae la carpeta dentro de `modelos`, de forma que quede así:

   ```text
   modelos/vosk-model-small-es-0.42/am
   modelos/vosk-model-small-es-0.42/conf
   modelos/vosk-model-small-es-0.42/graph
   modelos/vosk-model-small-es-0.42/ivector
   ```

   La carpeta `modelos/` se mantiene en el ordenador y está excluida de Git.

4. Configura `.env` con el ID de tu agente y la clave API:

   ```env
   AGENT_ID=tu-agent-id
   ELEVENLABS_API_KEY=tu-clave-api
   ```

   No subas `.env` ni compartas la clave API. Para agentes que requieren autenticación, la clave debe tener permiso de escritura de ElevenAgents para obtener la URL firmada de la conversación.

## Ejecutar

Desde la carpeta del proyecto, con el entorno virtual activado:

```powershell
python asistente.py
```

Sin activar el entorno virtual, también puedes ejecutar:

```powershell
py -3.13 asistente.py
```

## Seguimiento del proyecto

- `main`: base estable.
- `feature/elevenagents-architecture`: arquitectura y configuración inicial.
- `feature/voice-session`: primera sesión de conversación.
- `feature/agent-config`: validación de la configuración local.
- `feature/agent-setup-script`: creación de un agente mediante la API.
- `feature/wake-word`: activación local por frase con Vosk.

Los avances se registran en commits pequeños, explicados por fase.
