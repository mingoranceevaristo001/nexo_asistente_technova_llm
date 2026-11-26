# NEXO — Asistente de TechNova

NEXO es un chat que permite conversar con un modelo de reglas o con un modelo de lenguaje. La interfaz web es la forma principal de usarlo.

## Requisitos

- Python 3.9 o posterior.
- Una clave de Groq y conexión a internet si quieres usar **NEXO · LLM**. **NEXO · Reglas** funciona sin clave.

## Instalar y arrancar

Desde la carpeta raíz del proyecto, instala las dependencias:

```bash
python -m pip install -r nexo/requirements.txt
```

Inicia la aplicación:

```bash
cd nexo
python main.py
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000) en el navegador.

## Elegir el modelo

- **NEXO · Reglas** funciona sin conexión y responde a funciones básicas.
- **NEXO · LLM** permite hacer preguntas abiertas y requiere una clave de Groq.

Para configurar la clave, crea `nexo/.env` con este contenido:

```dotenv
GROQ_API_KEY=tu_clave_de_groq
```

Reemplaza el ejemplo por tu clave real. No la compartas ni subas el archivo `.env` a GitHub.

## Conversaciones

Usa **Nuevo chat** para empezar una conversación. Puedes volver a abrir chats anteriores desde la barra lateral o eliminarlos con el botón de papelera. Los chats se guardan en `nexo/datos/` en este equipo; evita incluir información confidencial.

Para usar la interfaz de consola en lugar de la web, ejecuta `python main.py --terminal` desde la carpeta `nexo/`.

Las respuestas de un modelo de lenguaje pueden contener errores; comprueba la información importante antes de utilizarla.
