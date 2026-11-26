import pytest

from dominio.excepciones import LimiteContextoSuperado
from dominio.mensaje import Conversacion, Mensaje


def test_mensaje_rechaza_un_rol_invalido():
    with pytest.raises(ValueError):
        Mensaje("desconocido", "Hola")


def test_agregar_no_guarda_un_mensaje_que_supera_el_limite():
    conversacion = Conversacion(limite_tokens=1)
    conversacion.agregar(Mensaje("usuario", "uno"))

    with pytest.raises(LimiteContextoSuperado):
        conversacion.agregar(Mensaje("usuario", "dos"))

    assert [mensaje.contenido for mensaje in conversacion.get_mensajes()] == ["uno"]


def test_get_mensajes_devuelve_una_copia():
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Hola"))

    mensajes = conversacion.get_mensajes()
    mensajes.clear()

    assert len(conversacion) == 1


def test_conversacion_por_defecto_acepta_mas_de_500_tokens_estimados():
    conversacion = Conversacion()
    contenido = "palabra " * 600

    conversacion.agregar(Mensaje("usuario", contenido))

    assert conversacion.tokens_estimados() > 500
    assert len(conversacion) == 1


def test_tokens_estimados_redondea_palabras():
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "uno dos tres cuatro"))

    assert conversacion.tokens_estimados() == 5


def test_to_dict_y_from_dict_reconstruyen_la_conversacion():
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Hola"))
    conversacion.agregar(Mensaje("asistente", "¡Buenas!"))

    reconstruida = Conversacion.from_dict(conversacion.to_dict())

    assert reconstruida.to_dict() == conversacion.to_dict()
