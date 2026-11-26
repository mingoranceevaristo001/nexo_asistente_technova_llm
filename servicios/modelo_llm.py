import json
import math
import os
from typing import Callable, Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from dominio.excepciones import ErrorModelo
from dominio.modelos import Modelo, ModeloReglas, Respuesta
from persistencia.registro_uso_llm import RegistroUsoLLM


API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_POR_DEFECTO = "openai/gpt-oss-20b"
MAX_TOKENS_POR_DEFECTO = 2048
ROLES_API = {"usuario": "user", "asistente": "assistant", "herramienta": "user"}
SYSTEM_PROMPT = (
    "Eres NEXO, el asistente de TechNova. Responde en español, de forma clara y útil. "
    "Cuando recibas un mensaje que empieza por 'Resultado de herramienta de NEXO:', "
    "utiliza ese resultado como fuente fiable para responder. No inventes datos de la "
    "tienda, tasas de cambio ni resultados de cálculos; si la herramienta indica que "
    "no encontró información, dilo claramente."
)


def _es_error_reintentable(error):
    if not isinstance(error, httpx.HTTPStatusError):
        return False
    if error.response.status_code == 429:
        try:
            detalle = error.response.json().get("error", {})
        except (ValueError, AttributeError, httpx.ResponseNotRead):
            detalle = {}
        return detalle.get("code") != "insufficient_quota"
    return error.response.status_code >= 500


def _mensaje_error_http(error):
    status = error.response.status_code
    try:
        detalle = error.response.json().get("error", {})
    except (ValueError, AttributeError, httpx.ResponseNotRead):
        detalle = {}

    mensaje = detalle.get("message")
    codigo = detalle.get("code") or detalle.get("type")
    if mensaje:
        sufijo = f" ({codigo})" if codigo else ""
        return f"El proveedor LLM respondió con HTTP {status}{sufijo}: {mensaje}"
    if status == 429:
        return (
            "El proveedor LLM respondió con HTTP 429. Comprueba los límites de uso "
            "y la facturación de tu cuenta API."
        )
    return f"El proveedor LLM respondió con HTTP {status}."


class ModeloLLM(Modelo):
    """Modelo remoto OpenAI compatible con el contrato de NEXO."""

    transmite_respuesta = True

    def __init__(
        self,
        modelo=None,
        max_tokens=None,
        temperature=0.7,
        registro=None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        if not api_key:
            raise ErrorModelo(
                "Falta GROQ_API_KEY (o LLM_API_KEY). Añádela al archivo .env "
                "antes de elegir /modelo llm."
            )

        modelo = modelo or os.getenv("GROQ_MODEL", MODELO_POR_DEFECTO)
        if max_tokens is None:
            limite_configurado = os.getenv(
                "GROQ_MAX_COMPLETION_TOKENS", str(MAX_TOKENS_POR_DEFECTO)
            )
            try:
                max_tokens = int(limite_configurado)
            except ValueError as error:
                raise ErrorModelo(
                    "GROQ_MAX_COMPLETION_TOKENS debe ser un entero positivo."
                ) from error
        super().__init__(f"ModeloLLM ({modelo})")
        self.modelo = modelo
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._api_key = api_key
        self._registro = registro or RegistroUsoLLM()
        self.on_chunk = on_chunk
        self._validar_parametros(max_tokens, temperature)

    @staticmethod
    def _validar_parametros(max_tokens, temperature):
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ErrorModelo("max_tokens debe ser un entero mayor que cero.")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)
            or not 0 <= temperature <= 2
        ):
            raise ErrorModelo("temperature debe estar dentro del rango [0, 2].")

    @staticmethod
    def _validar_mensajes(mensajes):
        if not mensajes:
            raise ErrorModelo("La conversación no puede estar vacía.")
        if mensajes[0].rol != "usuario":
            raise ErrorModelo("El primer mensaje debe tener el rol 'usuario'.")
        for mensaje in mensajes:
            if mensaje.rol not in ROLES_API:
                raise ErrorModelo(f"Rol de mensaje no admitido: {mensaje.rol}.")
            if not isinstance(mensaje.contenido, str):
                raise ErrorModelo("El contenido de cada mensaje debe ser texto.")

    def responder(self, conversacion, herramientas) -> Respuesta:
        mensajes = conversacion.get_mensajes()
        self._validar_mensajes(mensajes)
        self._validar_parametros(self.max_tokens, self.temperature)
        if mensajes[-1].rol == "usuario":
            respuesta_reglas = ModeloReglas().responder(conversacion, herramientas)
            nombres_herramientas = {herramienta.nombre for herramienta in herramientas}
            if (
                respuesta_reglas.es_llamada_herramienta()
                and respuesta_reglas.herramienta in nombres_herramientas
            ):
                return respuesta_reglas

        payload = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "max_completion_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        for mensaje in mensajes:
            contenido = mensaje.contenido
            if mensaje.rol == "herramienta":
                contenido = f"Resultado de herramienta de NEXO: {contenido}"
            payload["messages"].append(
                {"role": ROLES_API[mensaje.rol], "content": contenido}
            )

        try:
            texto, tokens_salida = self._solicitar_stream(payload)
        except httpx.HTTPStatusError as error:
            raise ErrorModelo(_mensaje_error_http(error)) from error
        except httpx.RequestError as error:
            raise ErrorModelo("No se pudo conectar con el proveedor LLM.") from error

        pregunta = next(
            mensaje.contenido for mensaje in reversed(mensajes) if mensaje.rol == "usuario"
        )
        try:
            self._registro.registrar(pregunta, tokens_salida)
        except OSError as error:
            raise ErrorModelo("No se pudo guardar el uso del modelo en el CSV.") from error

        return Respuesta(texto=texto)

    @retry(
        retry=retry_if_exception(_es_error_reintentable),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _solicitar_stream(self, payload):
        partes = []
        tokens_salida = None
        headers = {"Authorization": f"Bearer {self._api_key}"}

        with httpx.stream(
            "POST",
            API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        ) as response:
            if response.is_error:
                # Read the error body before raise_for_status so its JSON is available.
                response.read()
            response.raise_for_status()
            for linea in response.iter_lines():
                if isinstance(linea, bytes):
                    linea = linea.decode("utf-8")
                if not linea.startswith("data:"):
                    continue

                contenido = linea[len("data:"):].strip()
                if contenido == "[DONE]":
                    break
                try:
                    evento = json.loads(contenido)
                except json.JSONDecodeError as error:
                    raise ErrorModelo("El proveedor devolvió un evento SSE inválido.") from error

                uso = evento.get("usage")
                if uso is not None:
                    tokens_salida = uso.get("completion_tokens")

                for opcion in evento.get("choices", []):
                    fragmento = opcion.get("delta", {}).get("content")
                    if isinstance(fragmento, str):
                        partes.append(fragmento)
                        if self.on_chunk is not None:
                            self.on_chunk(fragmento)

        if tokens_salida is None:
            raise ErrorModelo("El proveedor no devolvió el uso de tokens de salida.")
        return "".join(partes), tokens_salida
