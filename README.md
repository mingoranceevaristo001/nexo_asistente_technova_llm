# NEXO Conectado con un LLM

## 1. Cómo ejecutar el proyecto

Hace falta Python 3.9 o superior. Instala las dependencias desde la raíz del repositorio:

```
python -m pip install -r nexo/requirements.txt
python -m pip install pytest
```

```
cd nexo
python main.py
```

(La aplicación se abre en `http://127.0.0.1:5000`. Ejecuta el comando desde dentro de `nexo/` para que la carpeta `datos/` se cree en su sitio. Para usar la interfaz anterior de terminal, ejecuta `python main.py --terminal`.)

En la barra lateral se guardan automáticamente los chats en `datos/conversaciones/`. Usa **Nuevo chat** para empezar otro y selecciona cualquiera de los anteriores para volver a abrirlo; el historial se conserva al cerrar y reiniciar la aplicación. Usa el botón de papelera de un chat para eliminarlo permanentemente, tras confirmar la acción.

## 2. Conectar con el modelo LLM de Groq

NEXO inicia con `ModeloReglas`, por lo que funciona sin conexión ni clave. Para usar la API de Groq:

1. Crea un archivo `.env` dentro de `nexo/`, junto a `main.py`.
2. Añade tu clave de Groq como `GROQ_API_KEY=...`. También se acepta `LLM_API_KEY=...` por compatibilidad. No compartas ni subas `.env`; está excluido por `.gitignore`.
3. En la web, elige **NEXO · LLM** en el selector de modelo. Para volver al modo local, elige **NEXO · Reglas**.

NEXO usa la API compatible con OpenAI de Groq (`https://api.groq.com/openai/v1`) y el modelo `openai/gpt-oss-20b` por defecto. Puedes establecer `GROQ_MODEL` en `.env` para elegir otro modelo disponible en tu cuenta. Las respuestas se procesan en streaming; las peticiones se validan antes de enviarse y se reintentan hasta cinco veces únicamente para límites HTTP 429 transitorios y errores 5xx.

Por defecto, cada respuesta puede generar hasta 2048 tokens y el historial de la conversación admite hasta 8000 tokens estimados. Para cambiar el límite de salida, añade `GROQ_MAX_COMPLETION_TOKENS=2500` a `.env` (usa el máximo permitido por el modelo de Groq que hayas elegido). El límite del historial de entrada es independiente.

El uso de tokens devuelto por el proveedor se registra en `nexo/datos/uso_llm.csv`, separado de `nexo/datos/uso.csv`, que ya registra ejecuciones de herramientas. El coste sigue la fórmula educativa de `0.008` por cada mil tokens de salida; es una estimación, no el importe facturado por Groq.

## 3. Nivel alcanzado

**Nivel 2: agente con memoria, con los Retos 1, 3 y 5 del Nivel 3 realizados.**

## 4. Retos realizados

**Reto 1: Reloj.** El agente puede consultar la fecha y la hora actuales con la herramienta `reloj`.

**Reto 3: esquema() en JSON Schema.** Cada herramienta declara sus `PARAMETROS`; la clase base construye el esquema compatible con el formato de herramientas de Anthropic.

Para comprobar los esquemas, ejecuta desde la carpeta `nexo/`:

```
python -c "import json; from dominio.herramientas import Calculadora, ConversorMoneda, BuscadorFAQ, Reloj; print(json.dumps([h.esquema() for h in (Calculadora(), ConversorMoneda(), BuscadorFAQ(), Reloj())], indent=2, ensure_ascii=False))"
```

El comando imprime el JSON Schema de cada herramienta en la terminal.

**Reto 5: tests con pytest.** La carpeta `tests/` contiene pruebas de mensajes, herramientas y modelos.

Para ejecutar las pruebas desde la carpeta del repositorio (o desde `nexo/`), instala pytest y ejecuta:

```
python -m pip install pytest
python -m pytest
```

Pytest solo es necesario para las pruebas; la aplicación sigue usando únicamente módulos estándar de Python.

## 5. Diagrama de clases

El diagrama editable de draw.io está en [`diagrama_clases_nexo.drawio`](./diagrama_clases/diagrama_clases_nexo.drawio). Puedes abrirlo o importarlo en [app.diagrams.net](https://app.diagrams.net/).

