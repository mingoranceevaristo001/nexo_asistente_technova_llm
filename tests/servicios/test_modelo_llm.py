import csv
import json
from unittest.mock import patch

import httpx
import pytest

from dominio.excepciones import ErrorModelo
from dominio.herramientas import Calculadora
from dominio.mensaje import Conversacion, Mensaje
from persistencia.registro_uso_llm import RegistroUsoLLM
from servicios.agente import Agente
from servicios.modelo_llm import API_URL, MODELO_POR_DEFECTO, ModeloLLM


class ResponseFalsa:
    def __init__(self, lineas, status_code=200, json_body=None):
        self.lineas = lineas
        self.status_code = status_code
        self._error_response = None
        if status_code >= 400:
            request = httpx.Request("POST", API_URL)
            contenido = (
                json.dumps(json_body).encode()
                if json_body is not None
                else b""
            )
            self._error_response = httpx.Response(
                status_code,
                request=request,
                stream=httpx.ByteStream(contenido),
            )

    @property
    def is_error(self):
        return self.status_code >= 400

    def read(self):
        if self._error_response is not None:
            self._error_response.read()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        if self._error_response is not None:
            self._error_response.raise_for_status()

    def iter_lines(self):
        return iter(self.lineas)


@pytest.fixture
def modelo(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MAX_COMPLETION_TOKENS", raising=False)
    registro = RegistroUsoLLM(str(tmp_path / "uso_llm.csv"))
    return ModeloLLM(registro=registro)


def test_modelo_llm_valida_mensajes_y_parametros(modelo):
    with pytest.raises(ErrorModelo, match="no puede estar vacía"):
        modelo._validar_mensajes([])

    with pytest.raises(ErrorModelo, match="primer mensaje"):
        modelo._validar_mensajes([Mensaje("asistente", "Hola")])

    with pytest.raises(ErrorModelo, match="max_tokens"):
        modelo._validar_parametros(0, 0.7)

    with pytest.raises(ErrorModelo, match="temperature"):
        modelo._validar_parametros(10, 2.1)


def test_modelo_llm_usa_groq_y_acepta_su_variable_de_clave(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MAX_COMPLETION_TOKENS", raising=False)
    monkeypatch.chdir(tmp_path)

    modelo_groq = ModeloLLM()

    assert modelo_groq._api_key == "groq-test-key"
    assert modelo_groq.modelo == "openai/gpt-oss-20b"
    assert modelo_groq.modelo == MODELO_POR_DEFECTO
    assert modelo_groq.max_tokens == 2048
    assert API_URL == "https://api.groq.com/openai/v1/chat/completions"


def test_modelo_llm_configura_limite_de_salida_desde_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_MAX_COMPLETION_TOKENS", "2500")
    monkeypatch.chdir(tmp_path)

    modelo_groq = ModeloLLM()

    assert modelo_groq.max_tokens == 2500


def test_modelo_llm_rechaza_limite_de_salida_no_numerico(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_MAX_COMPLETION_TOKENS", "muchos")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ErrorModelo, match="GROQ_MAX_COMPLETION_TOKENS"):
        ModeloLLM()


def test_modelo_llm_prefiere_groq_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("LLM_API_KEY", "other-key")
    monkeypatch.chdir(tmp_path)

    modelo_groq = ModeloLLM()

    assert modelo_groq._api_key == "groq-test-key"


def test_modelo_llm_envia_auth_y_modelo_a_groq(modelo):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Hola"))
    eventos = [
        'data: {"choices":[{"delta":{"content":"Hola"}}]}',
        'data: {"choices":[],"usage":{"completion_tokens":1}}',
        "data: [DONE]",
    ]

    with patch(
        "servicios.modelo_llm.httpx.stream",
        return_value=ResponseFalsa(eventos),
    ) as peticion:
        modelo.responder(conversacion, [])

    args, kwargs = peticion.call_args
    assert args[:2] == ("POST", API_URL)
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["json"]["model"] == MODELO_POR_DEFECTO
    assert kwargs["json"]["max_completion_tokens"] == 2048


def test_modelo_llm_transmite_fragmentos_y_registra_tokens(modelo, capsys, tmp_path):
    eventos = [
        'data: {"choices":[{"delta":{"content":"Hola "}}]}',
        'data: {"choices":[{"delta":{"content":"mundo"}}]}',
        'data: {"choices":[],"usage":{"completion_tokens":2}}',
        "data: [DONE]",
    ]
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Saluda"))

    with patch("servicios.modelo_llm.httpx.stream", return_value=ResponseFalsa(eventos)):
        modelo.on_chunk = lambda fragmento: print(fragmento, end="")
        respuesta = modelo.responder(conversacion, [])

    assert respuesta.texto == "Hola mundo"
    assert capsys.readouterr().out == "Hola mundo"
    with (tmp_path / "uso_llm.csv").open(newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert filas[0]["question"] == "Saluda"
    assert filas[0]["output_tokens"] == "2"
    assert filas[0]["cost"] == "0.00001600"


def test_modelo_llm_reintenta_429_y_no_reintenta_400(modelo):
    eventos = [
        'data: {"choices":[{"delta":{"content":"Listo"}}]}',
        'data: {"choices":[],"usage":{"completion_tokens":1}}',
        "data: [DONE]",
    ]
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Pregunta"))

    with (
        patch(
            "servicios.modelo_llm.httpx.stream",
            side_effect=[ResponseFalsa([], status_code=429), ResponseFalsa(eventos)],
        ) as peticion,
        patch("tenacity.nap.sleep"),
    ):
        respuesta = modelo.responder(conversacion, [])

    assert respuesta.texto == "Listo"
    assert peticion.call_count == 2

    with (
        patch(
            "servicios.modelo_llm.httpx.stream",
            return_value=ResponseFalsa([], status_code=400),
        ) as peticion,
        patch("tenacity.nap.sleep"),
        pytest.raises(ErrorModelo, match="HTTP 400"),
    ):
        modelo.responder(conversacion, [])

    assert peticion.call_count == 1


def test_modelo_llm_limita_a_cinco_intentos_en_429(modelo):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Pregunta"))

    with (
        patch(
            "servicios.modelo_llm.httpx.stream",
            return_value=ResponseFalsa([], status_code=429),
        ) as peticion,
        patch("tenacity.nap.sleep"),
        pytest.raises(ErrorModelo, match="HTTP 429"),
    ):
        modelo.responder(conversacion, [])

    assert peticion.call_count == 5


def test_modelo_llm_muestra_error_de_cuota_y_no_reintenta(modelo):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Pregunta"))

    with (
        patch(
            "servicios.modelo_llm.httpx.stream",
            return_value=ResponseFalsa(
                [],
                status_code=429,
                json_body={
                    "error": {
                        "code": "insufficient_quota",
                        "message": "You exceeded your current quota.",
                    }
                },
            ),
        ) as peticion,
        patch("tenacity.nap.sleep"),
        pytest.raises(ErrorModelo, match="insufficient_quota.*current quota"),
    ):
        modelo.responder(conversacion, [])

    assert peticion.call_count == 1


def test_modelo_llm_muestra_error_401_sin_response_not_read(modelo):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Hola"))

    with (
        patch(
            "servicios.modelo_llm.httpx.stream",
            return_value=ResponseFalsa(
                [],
                status_code=401,
                json_body={
                    "error": {
                        "code": "invalid_api_key",
                        "message": "Incorrect API key provided.",
                    }
                },
            ),
        ),
        pytest.raises(ErrorModelo, match="HTTP 401.*invalid_api_key.*Incorrect API key"),
    ):
        modelo.responder(conversacion, [])


def test_modelo_llm_usa_herramientas_nexo_y_envia_su_resultado(modelo, monkeypatch):
    payloads = []

    def respuesta_simulada(payload):
        payloads.append(payload)
        return "El resultado de 2 + 2 es 4.", 8

    monkeypatch.setattr(modelo, "_solicitar_stream", respuesta_simulada)
    agente = Agente(modelo, [Calculadora()])

    respuesta = agente.procesar("¿Cuánto es 2 + 2?")

    assert respuesta == "El resultado de 2 + 2 es 4."
    assert agente.llamadas_herramientas == [
        "calculadora(a=2, b=2, operacion='+')"
    ]
    assert payloads[0]["messages"][0]["role"] == "system"
    assert payloads[0]["messages"][-1] == {
        "role": "user",
        "content": "Resultado de herramienta de NEXO: 2 + 2 = 4",
    }
