import re

import pytest

from dominio.excepciones import ArgumentosInvalidos
from dominio.herramientas import (
    BuscadorFAQ,
    Calculadora,
    ConversorMoneda,
    Reloj,
)


def test_calculadora_multiplica():
    assert Calculadora().ejecutar(a=3, b=4, operacion="*") == "3 * 4 = 12"


@pytest.mark.parametrize(
    "argumentos",
    [
        {"a": 2, "b": 3, "operacion": "^"},
        {"a": 1, "b": 0, "operacion": "/"},
    ],
)
def test_calculadora_rechaza_operaciones_invalidas(argumentos):
    with pytest.raises(ArgumentosInvalidos):
        Calculadora().ejecutar(**argumentos)


def test_conversor_convierte_usd_a_eur():
    assert (
        ConversorMoneda().ejecutar(cantidad=250, origen="USD", destino="EUR")
        == "250 USD = 230.00 EUR"
    )


def test_conversor_rechaza_una_moneda_desconocida():
    with pytest.raises(ArgumentosInvalidos):
        ConversorMoneda().ejecutar(cantidad=10, origen="CAD", destino="EUR")


def test_buscador_faq_encuentra_una_respuesta():
    assert "envíos tardan" in BuscadorFAQ().ejecutar(pregunta="¿Cuánto tarda el envío?")


def test_buscador_faq_devuelve_no_encontrado_sin_coincidencias():
    assert BuscadorFAQ().ejecutar(pregunta="¿Cuál es el color del producto?") == "No encontrado"


def test_reloj_devuelve_fecha_y_hora_con_formato_correcto():
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", Reloj().ejecutar())


@pytest.mark.parametrize(
    ("herramienta", "input_schema"),
    [
        (
            Calculadora(),
            {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "Primer número"},
                    "b": {"type": "number", "description": "Segundo número"},
                    "operacion": {
                        "type": "string",
                        "enum": ["+", "-", "*", "/"],
                        "description": "Operación que se va a realizar",
                    },
                },
                "required": ["a", "b", "operacion"],
            },
        ),
        (
            ConversorMoneda(),
            {
                "type": "object",
                "properties": {
                    "cantidad": {
                        "type": "number",
                        "description": "Cantidad que se convierte",
                    },
                    "origen": {
                        "type": "string",
                        "enum": ["EUR", "USD", "GBP", "JPY"],
                        "description": "Moneda de origen",
                    },
                    "destino": {
                        "type": "string",
                        "enum": ["EUR", "USD", "GBP", "JPY"],
                        "description": "Moneda de destino",
                    },
                },
                "required": ["cantidad", "origen", "destino"],
            },
        ),
        (
            BuscadorFAQ(),
            {
                "type": "object",
                "properties": {
                    "pregunta": {
                        "type": "string",
                        "description": "Pregunta frecuente sobre la tienda",
                    }
                },
                "required": ["pregunta"],
            },
        ),
        (
            Reloj(),
            {"type": "object", "properties": {}, "required": []},
        ),
    ],
)
def test_esquema_incluye_nombre_descripcion_y_argumentos(herramienta, input_schema):
    esquema = herramienta.esquema()

    assert esquema["name"] == herramienta.nombre
    assert esquema["description"] == herramienta.descripcion
    assert esquema["input_schema"] == input_schema


def test_modificar_esquema_no_modifica_parametros_de_la_clase():
    esquema = Calculadora().esquema()
    esquema["input_schema"]["properties"]["a"]["type"] = "string"

    assert Calculadora.PARAMETROS["a"]["type"] == "number"
