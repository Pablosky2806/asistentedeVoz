# Mateo: asistente de voz para Windows

Proyecto en Python con dos motores de conversación:

- `asistente_local.py`: versión local para conversar sin consumir créditos de ElevenLabs. Usa Vosk para detectar la frase de activación, faster-whisper para transcribir con más precisión, Ollama con `qwen3:8b` para responder y Piper con la voz `es_ES-sharvard-medium` para hablar en español, sin emojis ni emoticonos. Mateo usa un trato cortés y pausado, inspirado en un mayordomo.
- `asistente.py`: versión anterior conectada a ElevenLabs; requiere una clave API y consume la cuota de esa cuenta.

## Cómo funciona la versión local

Vosk escucha el micrófono en el equipo y espera **«Oye, Mateo»** o **«Illo, Mateo»**. Después, faster-whisper transcribe cada turno localmente, Ollama genera la respuesta en el portátil y Piper la convierte en voz. Puedes despedirte con frases naturales como **«adiós»**, **«hasta luego»**, **«me voy»**, **«ya no te necesito»**, **«eso es todo»** o **«deja de escuchar»**. Mateo responderá y volverá a esperar la frase de activación.

Durante una conversación puedes pedirle que abra una aplicación o juego por su nombre, o una carpeta con frases como «abre Teams», «ábreme la carpeta Fotos» o «enséñame Descargas». Busca accesos directos del menú Inicio y el escritorio, aplicaciones que Windows registra en Inicio y carpetas del perfil de usuario y OneDrive. La búsqueda de carpetas se limita a cinco niveles de profundidad. Si hay nombres parecidos o carpetas duplicadas, pregunta cuál abrir. Para Disney+, WhatsApp y Teams puede abrir la versión web si no encuentra una aplicación local.

## Memoria personal y privacidad

Mateo solo guarda datos cuando se lo pides explícitamente con «recuerda que…». La memoria se guarda en `datos/memoria_mateo.json` en este equipo, no se sube a GitHub y solo se añade como contexto al modelo local cuando está activada. No guardes contraseñas, tokens ni claves de API.

- «¿Qué recuerdas de mí?» muestra los datos guardados.
- «Olvida que…» elimina un dato concreto.
- «Desactiva la memoria» conserva las notas, pero deja de usarlas y añadir nuevas.
- «Activa la memoria» vuelve a usar las notas existentes y permite guardar otras a petición.
- «Borra mi memoria» pide confirmación y elimina todos los datos guardados.

También puedes revisar o borrar el archivo local `datos/memoria_mateo.json` manualmente.

Los modelos se descargan una vez y quedan guardados localmente. La conversación no envía audio ni mensajes a ElevenLabs. El contexto se conserva durante la conversación actual. La memoria persistente opcional se guarda localmente y puedes controlarla desde el widget.

## Instalación sencilla en Windows

Requisitos: Windows, Python 3.13 y [Ollama para Windows](https://ollama.com/download/windows). Descarga el repositorio y abre PowerShell dentro de su carpeta. Ejecuta una vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\configurar_mateo.ps1
```

El instalador crea un entorno Python aislado en `.venv`, instala las dependencias y descarga los modelos de Vosk, Piper y Whisper que falten. Comprueba Ollama y configura el inicio automático de Mateo. Si falta `qwen3:8b`, te pregunta antes de iniciar una descarga de aproximadamente 5,2 GB. Si respondes que no, puedes descargarlo después con `ollama pull qwen3:8b` y volver a ejecutar el instalador.

La primera instalación puede tardar: Whisper ocupa alrededor de 500 MB y el modelo de Ollama varios GB. Los archivos se quedan en este equipo; `modelos/`, `.venv/` y `datos/` están excluidos de Git.

## Ejecutar Mateo sin créditos de API

Desde la carpeta del proyecto:

```powershell
.venv\Scripts\python.exe asistente_local.py
```

Pulsa `Ctrl+C` para salir. La velocidad de respuesta depende del procesador y del modelo local. Ollama y Piper usan los modelos descargados en el portátil.

Para abrir el widget flotante de Mateo, ejecuta el acceso directo de Inicio o, desde la carpeta del proyecto:

```powershell
wscript.exe .\iniciar_mateo.vbs
```

## Inicio automático

`widget_mateo.py` muestra una cápsula flotante arriba de la pantalla con el icono y estado de Mateo. Al desplegarla se ve la actividad reciente, puedes pausar o reanudar el micrófono, activar o desactivar la memoria, abrir su archivo local o borrarla con confirmación. `iniciar_mateo.vbs` abre el widget sin consola y `detener_mateo.vbs` cierra el widget y el asistente. El instalador configura el inicio automático al iniciar sesión en Windows; para configurarlo manualmente puedes ejecutar:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar_inicio_automatico.ps1
```

Windows no permite que Mateo escuche antes de iniciar sesión; se abrirá después de entrar en tu cuenta. Al iniciar, Mateo comprueba que Ollama responde y prepara `qwen3:8b` antes de empezar a escuchar. Para desactivar el inicio automático, elimina el acceso directo `Mateo.lnk` de la carpeta Inicio de Windows. El widget usa el entorno `.venv` del proyecto; si no está, intenta usar Python 3.13 instalado en el perfil de Windows.

## Seguimiento del proyecto

- `main`: base estable.
- `feature/elevenagents-architecture`: arquitectura de ElevenAgents.
- `feature/voice-session`: primera sesión de conversación.
- `feature/agent-config`: validación de configuración.
- `feature/agent-setup-script`: creación de agente mediante la API.
- `feature/wake-word`: activación local por frase con Vosk.
- `feature/local-ai`: conversación local con Vosk, Ollama y Piper.

Los cambios se registran en commits pequeños por fase.
