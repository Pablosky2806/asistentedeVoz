# Mateo: asistente de voz para Windows

Proyecto en Python con dos motores de conversación:

- `asistente_local.py`: versión local para conversar sin consumir créditos de ElevenLabs. Usa Vosk para detectar la frase de activación, faster-whisper para transcribir con más precisión, Ollama con `qwen3:8b` para responder y Piper con la voz `es_ES-sharvard-medium` para hablar en español, sin emojis ni emoticonos. Mateo usa un trato cortés y pausado, inspirado en un mayordomo.
- `asistente.py`: versión anterior conectada a ElevenLabs; requiere una clave API y consume la cuota de esa cuenta.

## Cómo funciona la versión local

Vosk escucha el micrófono en el equipo y espera **«Oye, Mateo»** o **«Illo, Mateo»**. Después, faster-whisper transcribe cada turno localmente, Ollama genera la respuesta en el portátil y Piper la convierte en voz. Puedes despedirte con frases naturales como **«adiós»**, **«hasta luego»**, **«me voy»**, **«ya no te necesito»**, **«eso es todo»** o **«deja de escuchar»**. Mateo responderá y volverá a esperar la frase de activación.

Durante una conversación puedes pedirle que abra una aplicación o juego por su nombre, o una carpeta con frases como «abre Teams», «ábreme la carpeta Fotos» o «enséñame Descargas». Busca accesos directos del menú Inicio y el escritorio, aplicaciones que Windows registra en Inicio y carpetas del perfil de usuario y OneDrive. La búsqueda de carpetas se limita a cinco niveles de profundidad. Si hay nombres parecidos o carpetas duplicadas, pregunta cuál abrir. Para Disney+, WhatsApp y Teams puede abrir la versión web si no encuentra una aplicación local.

Los modelos se descargan una vez y quedan guardados localmente. La conversación no envía audio ni mensajes a ElevenLabs. El contexto se conserva durante la conversación actual; la memoria persistente se añadirá en otra fase.

## Preparación en Windows

Se recomienda Python 3.13 para usar PyAudio en Windows.

1. Crea y activa un entorno virtual:

   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Instala las dependencias:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Descarga el modelo pequeño de español de [Vosk](https://alphacephei.com/vosk/models) (`vosk-model-small-es-0.42`, unos 39 MB). Extrae la carpeta en `modelos`, para que exista `modelos/vosk-model-small-es-0.42/conf`.

4. Instala [Ollama para Windows](https://ollama.com/download/windows). Luego abre PowerShell y descarga el modelo local de 8B:

   ```powershell
   ollama run qwen3:8b
   ```

   La descarga ocupa unos 5,2 GB. Cuando aparezca el indicador de conversación de Ollama, escribe `/bye` para salir. El modelo permanece en el equipo y Ollama atiende las solicitudes locales.

5. Descarga la nueva voz española de Piper dentro de `modelos/piper`:

   ```powershell
   New-Item -ItemType Directory -Force modelos\piper
   py -3.13 -m piper.download_voices es_ES-sharvard-medium --data-dir modelos\piper
   ```

La carpeta `modelos/` está excluida de Git para no subir archivos grandes. En el primer arranque, faster-whisper descarga una vez su modelo de reconocimiento; después la transcripción funciona localmente.

## Ejecutar Mateo sin créditos de API

Desde la carpeta del proyecto:

```powershell
py -3.13 asistente_local.py
```

Pulsa `Ctrl+C` para salir. La velocidad de respuesta depende del procesador y del modelo local. Ollama y Piper usan los modelos descargados en el portátil.

Para abrir el widget flotante de Mateo, ejecuta:

```powershell
py -3.13 widget_mateo.py
```

## Inicio automático

`widget_mateo.py` muestra una cápsula flotante arriba de la pantalla con el icono y estado de Mateo. Al desplegarla se ve la actividad reciente y los controles. `iniciar_mateo.vbs` abre el widget sin consola y `detener_mateo.vbs` cierra el widget y el asistente. Para que Mateo se inicie automáticamente al iniciar sesión en Windows, ejecuta una vez `instalar_inicio_automatico.ps1` desde PowerShell en la carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_inicio_automatico.ps1
```

Windows no permite que Mateo escuche antes de iniciar sesión; se abrirá después de entrar en tu cuenta. Al iniciar, Mateo comprueba que Ollama responde, busca `qwen3:8b` y lo prepara antes de empezar a escuchar. Si el modelo no está descargado, Mateo te lo indicará y podrás instalarlo con `ollama pull qwen3:8b`. Para desactivar el inicio automático, elimina el acceso directo `Mateo.lnk` de la carpeta Inicio de Windows.

## Seguimiento del proyecto

- `main`: base estable.
- `feature/elevenagents-architecture`: arquitectura de ElevenAgents.
- `feature/voice-session`: primera sesión de conversación.
- `feature/agent-config`: validación de configuración.
- `feature/agent-setup-script`: creación de agente mediante la API.
- `feature/wake-word`: activación local por frase con Vosk.
- `feature/local-ai`: conversación local con Vosk, Ollama y Piper.

Los cambios se registran en commits pequeños por fase.
