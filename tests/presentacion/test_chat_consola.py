from dominio.excepciones import HerramientaNoEncontrada
from dominio.modelos import ModeloEco
from presentacion.chat_consola import ChatConsola
from servicios.agente import Agente


class RepositorioFalso:
    def listar(self):
        return []


class AgenteQueFalla:
    llamadas_herramientas = []

    def procesar(self, texto):
        raise HerramientaNoEncontrada("herramienta desconocida")


def test_iniciar_procesa_mensajes_y_termina_con_comando_salir(monkeypatch, capsys):
    agente = Agente(ModeloEco(), [])
    chat = ChatConsola(agente, RepositorioFalso())
    entradas = iter(["", "Hola", "/salir"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))

    chat.iniciar()

    salida = capsys.readouterr().out
    assert "NEXO > Has dicho: Hola" in salida
    assert "¡Hasta pronto!" in salida
    assert [mensaje.contenido for mensaje in agente.conversacion.get_mensajes()] == [
        "Hola",
        "Has dicho: Hola",
    ]


def test_iniciar_muestra_error_del_agente_y_sigue_aceptando_entradas(
    monkeypatch, capsys
):
    chat = ChatConsola(AgenteQueFalla(), RepositorioFalso())
    entradas = iter(["mensaje", "/salir"])
    monkeypatch.setattr("builtins.input", lambda _: next(entradas))

    chat.iniciar()

    salida = capsys.readouterr().out
    assert "⚠ herramienta desconocida" in salida
    assert "¡Hasta pronto!" in salida


def test_iniciar_finaliza_si_la_entrada_llega_a_eof(monkeypatch, capsys):
    chat = ChatConsola(Agente(ModeloEco(), []), RepositorioFalso())

    def entrada_fin(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", entrada_fin)

    chat.iniciar()

    assert "¡Hasta pronto!" in capsys.readouterr().out


def test_comando_cargar_informa_que_falta_el_id(capsys):
    chat = ChatConsola(Agente(ModeloEco(), []), RepositorioFalso())

    chat._ejecutar_comando("/cargar")

    assert "Uso: /cargar <id>" in capsys.readouterr().out
