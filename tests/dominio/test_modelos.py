import pytest

from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import ModeloEco, ModeloReglas


@pytest.mark.parametrize(
    ("texto", "herramienta"),
    [
        ("3 * 4", "calculadora"),
        ("250 USD", "conversor_moneda"),
        ("envío", "buscador_faq"),
        ("qué hora es", "reloj"),
    ],
)
def test_modelo_reglas_pide_la_herramienta_correcta(texto, herramienta):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", texto))

    respuesta = ModeloReglas().responder(conversacion, [])

    assert respuesta.herramienta == herramienta
    assert respuesta.es_llamada_herramienta()


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("hola", "¡Hola! Soy NEXO, ¿en qué te ayudo?"),
        ("asdf qwer zxcv", "No estoy seguro, ¿puedes reformularlo?"),
    ],
)
def test_modelo_reglas_saluda_o_pide_reformular(texto, esperado):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", texto))

    respuesta = ModeloReglas().responder(conversacion, [])

    assert respuesta.texto == esperado
    assert not respuesta.es_llamada_herramienta()


def test_modelo_eco_repite_el_mensaje_del_usuario():
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Prueba del modelo eco"))

    respuesta = ModeloEco().responder(conversacion, [])

    assert respuesta.texto == "Has dicho: Prueba del modelo eco"
