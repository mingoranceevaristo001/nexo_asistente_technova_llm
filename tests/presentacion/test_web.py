import json

import pytest

from dominio.excepciones import ErrorModelo
from dominio.herramientas import Calculadora, Reloj
from dominio.modelos import ModeloEco, ModeloReglas
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from persistencia.registro_uso_llm import RegistroUsoLLM
from servicios.agente import Agente
from servicios.modelo_llm import ModeloLLM
from presentacion.web import crear_app


def crear_app_prueba(agente, tmp_path):
    repositorio = RepositorioConversaciones(str(tmp_path / "conversaciones"))
    return crear_app(agente, repositorio)


@pytest.fixture
def client(tmp_path):
    app = crear_app_prueba(Agente(ModeloEco(), []), tmp_path)
    app.config.update(TESTING=True)
    return app.test_client()


def test_pagina_principal_muestra_interfaz_de_chat(client):
    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert b"NEXO" in respuesta.data
    assert b"Escribe un mensaje" in respuesta.data
    assert b"conversation-delete" in respuesta.data
    assert "Esta acción no se puede deshacer".encode("utf-8") in respuesta.data
    assert 'role === "user" ? "TÚ" : "NEXO"'.encode("utf-8") in respuesta.data
    assert b'id="robot-sprite"' in respuesta.data
    assert b'src="/sprites/Nexo_reposo.png"' in respuesta.data
    assert b"Nexo_pensando.png" in respuesta.data
    assert b"Nexos_respondiendo.png" in respuesta.data
    assert b"Nexo_terminado.png" in respuesta.data
    assert b"id=\"mascot\"" in respuesta.data
    assert b'robotSprites[state] || robotSprites.ready' in respuesta.data
    assert "NEXO está hablando".encode("utf-8") in respuesta.data
    html = respuesta.get_data(as_text=True)
    floating_position = html.index('class="floating-ui"')
    robot_position = html.index('id="mascot"')
    tools_position = html.index('id="show-tools"')
    model_position = html.index('id="model"')
    sidebar_position = html.index('<aside class="sidebar">')
    conversations_position = html.index('id="conversation-list"')
    new_chat_position = html.index('id="new-chat"')
    messages_position = html.index('id="messages"')
    assert floating_position < robot_position < tools_position < model_position < sidebar_position
    assert "position: fixed; z-index: 20" in html
    assert "position: fixed; z-index: 10" in html
    assert "position: fixed; top: 14px; left: 50%" in html
    assert "transform: translateX(-50%)" in html
    assert "top: 60px; right: 8px" in html
    assert "flex: 1 1 auto" in html
    assert "min-height: 0; overflow-x: hidden; overflow-y: auto" in html
    assert "white-space: normal; overflow-wrap: anywhere" in html
    assert sidebar_position < new_chat_position < conversations_position < messages_position
    assert robot_position < new_chat_position < messages_position


@pytest.mark.parametrize(
    "filename",
    [
        "Nexo_reposo.png",
        "Nexo_pensando.png",
        "Nexos_respondiendo.png",
        "Nexo_terminado.png",
    ],
)
def test_sprites_del_robot_se_sirven_desde_flask(client, filename):
    respuesta = client.get(f"/sprites/{filename}")

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "image/png"
    assert respuesta.data


def test_lista_herramientas_devuelve_herramientas_del_agente(tmp_path):
    app = crear_app_prueba(Agente(ModeloReglas(), [Calculadora(), Reloj()]), tmp_path)
    app.config.update(TESTING=True)

    respuesta = app.test_client().get("/api/herramientas")

    assert respuesta.status_code == 200
    assert respuesta.json["tools"] == [
        "🔧 calculadora: Suma, resta, multiplica y divide dos números (+ - * /)",
        "🔧 reloj: Dice la fecha y la hora actuales",
    ]


def test_interfaz_incluye_acceso_a_la_lista_de_herramientas(client):
    respuesta = client.get("/")

    assert b"Herramientas" in respuesta.data
    assert b"/api/herramientas" in respuesta.data


def test_chat_envia_mensaje_y_emite_evento_sse(client):
    respuesta = client.post("/api/chat", json={"message": "Hola"})
    eventos = [
        json.loads(line.removeprefix("data: "))
        for line in respuesta.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "text/event-stream"
    assert eventos[-1]["type"] == "done"
    assert eventos[-1]["text"] == "Has dicho: Hola"


def test_chat_rechaza_mensaje_vacio(client):
    respuesta = client.post("/api/chat", json={"message": "   "})

    assert respuesta.status_code == 400
    assert "Escribe un mensaje" in respuesta.json["error"]


def test_chat_emite_el_detalle_del_error_del_modelo(tmp_path):
    class ModeloConError:
        def responder(self, conversacion, herramientas):
            raise ErrorModelo("HTTP 429: cuota API agotada")

    app = crear_app_prueba(Agente(ModeloConError(), []), tmp_path)
    app.config.update(TESTING=True)

    respuesta = app.test_client().post("/api/chat", json={"message": "hola"})
    eventos = [
        json.loads(line.removeprefix("data: "))
        for line in respuesta.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]

    assert eventos[-1] == {
        "type": "error",
        "message": "HTTP 429: cuota API agotada",
    }


def test_cambiar_modelo_a_reglas(client):
    respuesta = client.post("/api/modelo", json={"name": "reglas"})

    assert respuesta.status_code == 200
    assert respuesta.json["name"] == "reglas"


def test_cambiar_modelo_llm_sin_clave_da_error_claro(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.chdir(tmp_path)
    app = crear_app_prueba(Agente(ModeloReglas(), []), tmp_path)
    app.config.update(TESTING=True)

    respuesta = app.test_client().post("/api/modelo", json={"name": "llm"})

    assert respuesta.status_code == 400
    assert "Falta GROQ_API_KEY" in respuesta.json["error"]


def test_streaming_llm_se_envia_como_eventos_sse(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    modelo = ModeloLLM(registro=RegistroUsoLLM(str(tmp_path / "uso.csv")))

    def respuesta_simulada(payload):
        modelo.on_chunk("Hola ")
        modelo.on_chunk("web")
        return "Hola web", 2

    monkeypatch.setattr(modelo, "_solicitar_stream", respuesta_simulada)
    app = crear_app_prueba(Agente(modelo, []), tmp_path)
    app.config.update(TESTING=True)

    respuesta = app.test_client().post("/api/chat", json={"message": "Saluda"})
    eventos = [
        json.loads(line.removeprefix("data: "))
        for line in respuesta.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]

    assert [evento["text"] for evento in eventos if evento["type"] == "chunk"] == [
        "Hola ",
        "web",
    ]
    assert eventos[-1] == {"type": "done", "text": "Hola web", "tools": []}


def test_guarda_y_permite_cambiar_entre_conversaciones(client):
    respuesta = client.post("/api/chat", json={"message": "Primer chat"})
    eventos = [
        json.loads(line.removeprefix("data: "))
        for line in respuesta.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]
    assert eventos[-1]["type"] == "done"

    primera_lista = client.get("/api/conversaciones").json["conversations"]
    assert len(primera_lista) == 1
    primer_id = primera_lista[0]["id"]
    assert primera_lista[0]["title"] == "Primer chat"

    respuesta = client.post("/api/nueva")
    assert respuesta.status_code == 200
    segundo_id = respuesta.json["id"]
    assert segundo_id != primer_id

    client.post("/api/chat", json={"message": "Segundo chat"})
    lista = client.get("/api/conversaciones").json["conversations"]
    assert {conversacion["id"] for conversacion in lista} == {primer_id, segundo_id}

    respuesta = client.post(f"/api/conversaciones/{primer_id}")
    assert respuesta.status_code == 200
    historial = client.get("/api/historial").json["messages"]
    assert historial == [
        {"role": "user", "content": "Primer chat"},
        {"role": "assistant", "content": "Has dicho: Primer chat"},
    ]


def test_titulo_de_chat_muestra_el_mensaje_completo(client):
    titulo = "Este es un mensaje inicial bastante largo para comprobar que no se corta a los 48 caracteres"

    client.post("/api/chat", json={"message": titulo})

    conversaciones = client.get("/api/conversaciones").json["conversations"]
    assert conversaciones[0]["title"] == titulo


def test_eliminar_conversacion_activa_la_borra_y_abre_un_chat_vacio(client):
    client.post("/api/chat", json={"message": "Borrar este chat"})
    id_conv = client.get("/api/conversaciones").json["conversations"][0]["id"]

    respuesta = client.delete(f"/api/conversaciones/{id_conv}")

    assert respuesta.status_code == 200
    assert respuesta.json == {"ok": True, "active": True}
    assert client.get("/api/conversaciones").json["conversations"] == []
    assert client.get("/api/historial").json["messages"] == []


def test_eliminar_conversacion_rechaza_id_invalido_y_chat_inexistente(client):
    invalida = client.delete("/api/conversaciones/no-valido")
    inexistente = client.delete("/api/conversaciones/12345678")

    assert invalida.status_code == 400
    assert inexistente.status_code == 404


def test_rechaza_id_de_conversacion_no_valido(client):
    respuesta = client.post("/api/conversaciones/../../etc")

    assert respuesta.status_code in (400, 404)


def test_conversacion_guardada_se_puede_recuperar_tras_reiniciar_app(tmp_path):
    repositorio = RepositorioConversaciones(str(tmp_path / "conversaciones"))
    primera_app = crear_app(Agente(ModeloEco(), []), repositorio)
    primera_app.config.update(TESTING=True)
    primer_cliente = primera_app.test_client()

    primer_cliente.post("/api/chat", json={"message": "Recordar esto"})
    id_conv = primer_cliente.get("/api/conversaciones").json["conversations"][0]["id"]

    segunda_app = crear_app(Agente(ModeloEco(), []), repositorio)
    segunda_app.config.update(TESTING=True)
    segundo_cliente = segunda_app.test_client()

    assert segundo_cliente.get("/api/conversaciones").json["conversations"][0]["id"] == id_conv
    respuesta = segundo_cliente.post(f"/api/conversaciones/{id_conv}")

    assert respuesta.status_code == 200
    assert segundo_cliente.get("/api/historial").json["messages"] == [
        {"role": "user", "content": "Recordar esto"},
        {"role": "assistant", "content": "Has dicho: Recordar esto"},
    ]
