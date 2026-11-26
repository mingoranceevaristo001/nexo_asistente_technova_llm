class ErrorAgente(Exception):
    """Excepción base de NEXO."""


class HerramientaNoEncontrada(ErrorAgente):
    """El modelo ha pedido una herramienta que no existe."""


class ArgumentosInvalidos(ErrorAgente):
    """Los argumentos que recibe una herramienta no son correctos."""


class LimiteContextoSuperado(ErrorAgente):
    """La conversación supera el límite de tokens."""


class ErrorModelo(ErrorAgente):
    """Se ha producido un error al configurar o consultar un modelo."""
