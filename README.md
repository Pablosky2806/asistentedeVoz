# Asistente de voz con ElevenLabs

Proyecto en Python para mantener conversaciones por voz.

## Arquitectura elegida

La primera versión usará **ElevenAgents** mediante el SDK oficial de Python. ElevenLabs proporciona el agente conversacional y gestiona la entrada de voz, las transcripciones y el audio de respuesta. El SDK conecta el micrófono y los altavoces del equipo con una sesión del agente.

Esto requiere crear/configurar un agente en ElevenLabs y obtener su `AGENT_ID`. Si el agente es privado, también se necesitará `ELEVENLABS_API_KEY`. Las credenciales se guardarán localmente en un archivo `.env`, que Git ignora.

La sesión empieza cuando se ejecuta el programa y se cierra con `Ctrl+C`. No se incluye todavía una palabra de activación permanente (por ejemplo, «Oye asistente»); esa función necesitaría una fase aparte.

## Configuración local

1. Crear y activar un entorno virtual de Python.
2. Instalar las dependencias de `requirements.txt`.
3. Copiar `.env.example` a `.env` y completar los valores desde ElevenLabs.

No subas el archivo `.env` ni compartas la API key.

## Plan de trabajo

1. Preparar el repositorio y acordar la arquitectura. **En curso**
2. Configurar dependencias y secretos locales sin subir la API key.
3. Crear una primera conversación funcional.
4. Añadir activación por voz y controles básicos de la sesión.
5. Documentar la configuración, probar y publicar en GitHub.

Cada avance se hará en una rama y quedará registrado en commits pequeños y explicados.

## Estado

La arquitectura y la configuración base están definidas; aún no hay integración de código.
