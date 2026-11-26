import sys

from dominio.herramientas import Calculadora, ConversorMoneda, BuscadorFAQ, Reloj
from dominio.modelos import ModeloReglas
from servicios.agente import Agente
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from persistencia.registro_uso import RegistroUso
from presentacion.chat_consola import ChatConsola
from presentacion.web import crear_agente, crear_app

if __name__ == "__main__":
    if "--terminal" in sys.argv:
        herramientas = [Calculadora(), ConversorMoneda(), BuscadorFAQ(), Reloj()]
        agente = Agente(ModeloReglas(), herramientas, RegistroUso("datos/uso.csv"))
        ChatConsola(agente, RepositorioConversaciones()).iniciar()
    else:
        crear_app(crear_agente()).run(host="127.0.0.1", port=5000, debug=False, threaded=True)