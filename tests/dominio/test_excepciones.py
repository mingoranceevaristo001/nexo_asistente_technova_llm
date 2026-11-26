import pytest

from dominio.excepciones import (
    ArgumentosInvalidos,
    ErrorAgente,
    HerramientaNoEncontrada,
    LimiteContextoSuperado,
)


@pytest.mark.parametrize(
    "tipo_error",
    [HerramientaNoEncontrada, ArgumentosInvalidos, LimiteContextoSuperado],
)
def test_excepciones_especificas_heredan_de_error_agente(tipo_error):
    assert issubclass(tipo_error, ErrorAgente)
    assert issubclass(ErrorAgente, Exception)


def test_excepcion_conserva_su_mensaje():
    error = HerramientaNoEncontrada("La herramienta 'x' no existe")

    assert str(error) == "La herramienta 'x' no existe"
