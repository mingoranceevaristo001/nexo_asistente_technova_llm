import re
from copy import deepcopy
from datetime import datetime

from dominio.excepciones import ArgumentosInvalidos


class Herramienta:
    """Clase base de todas las herramientas que puede usar el agente."""

    PARAMETROS = {}

    def __init__(self, nombre, descripcion):
        self.nombre = nombre
        self.descripcion = descripcion

    def esquema(self) -> dict:
        return {
            "name": self.nombre,
            "description": self.descripcion,
            "input_schema": {
                "type": "object",
                "properties": deepcopy(self.PARAMETROS),
                "required": list(self.PARAMETROS),
            },
        }

    def ejecutar(self, **kwargs) -> str:
        raise NotImplementedError("Cada herramienta debe implementar ejecutar()")

    def __str__(self):
        return f"🔧 {self.nombre}: {self.descripcion}"


class Calculadora(Herramienta):
    PARAMETROS = {
        "a": {"type": "number", "description": "Primer número"},
        "b": {"type": "number", "description": "Segundo número"},
        "operacion": {
            "type": "string",
            "enum": ["+", "-", "*", "/"],
            "description": "Operación que se va a realizar",
        },
    }

    def __init__(self):
        super().__init__(
            "calculadora", "Suma, resta, multiplica y divide dos números (+ - * /)"
        )

    def ejecutar(self, **kwargs) -> str:
        a = kwargs.get("a")
        b = kwargs.get("b")
        operacion = kwargs.get("operacion")

        try:
            numero_a = float(a)
            numero_b = float(b)
        except (TypeError, ValueError):
            raise ArgumentosInvalidos("a y b tienen que ser números")

        if operacion == "+":
            resultado = numero_a + numero_b
        elif operacion == "-":
            resultado = numero_a - numero_b
        elif operacion == "*":
            resultado = numero_a * numero_b
        elif operacion == "/":
            if numero_b == 0:
                raise ArgumentosInvalidos("no se puede dividir entre 0")
            resultado = numero_a / numero_b
        else:
            raise ArgumentosInvalidos(f"operación no válida: {operacion}")

        # Redondeamos para quitar errores de decimales (3 * 79.9 daría 239.70000000000002)
        resultado = round(resultado, 6)
        if resultado == int(resultado):
            resultado = int(resultado)  # 12.0 se muestra como 12
        return f"{a} {operacion} {b} = {resultado}"


class ConversorMoneda(Herramienta):
    TASAS_A_EUR = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "JPY": 0.0062}
    PARAMETROS = {
        "cantidad": {"type": "number", "description": "Cantidad que se convierte"},
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
    }

    def __init__(self):
        super().__init__(
            "conversor_moneda", "Convierte una cantidad entre EUR, USD, GBP y JPY"
        )

    def ejecutar(self, **kwargs) -> str:
        cantidad = kwargs.get("cantidad")
        origen = kwargs.get("origen")
        destino = kwargs.get("destino")

        try:
            numero = float(cantidad)
        except (TypeError, ValueError):
            raise ArgumentosInvalidos("la cantidad tiene que ser un número")

        if origen not in self.TASAS_A_EUR or destino not in self.TASAS_A_EUR:
            monedas = ", ".join(self.TASAS_A_EUR)
            raise ArgumentosInvalidos(f"moneda no admitida (solo {monedas})")

        # Primero pasamos a euros y después a la moneda de destino
        euros = numero * self.TASAS_A_EUR[origen]
        resultado = euros / self.TASAS_A_EUR[destino]
        return f"{cantidad} {origen} = {resultado:.2f} {destino}"


class BuscadorFAQ(Herramienta):
    FAQ = {
        "envio plazo dias tarda": "Los envíos tardan 24-48 h en península y 3-5 días en islas.",
        "devolucion devolver garantia": "Tienes 30 días para devolver el producto sin dar explicaciones.",
        "horario atencion abierto": "Atendemos de lunes a viernes de 9:00 a 18:00.",
        "pago tarjeta bizum paypal": "Aceptamos tarjeta, Bizum y PayPal.",
    }
    PARAMETROS = {
        "pregunta": {
            "type": "string",
            "description": "Pregunta frecuente sobre la tienda",
        },
    }

    def __init__(self):
        super().__init__(
            "buscador_faq", "Busca la respuesta a una pregunta frecuente de la tienda"
        )

    def ejecutar(self, **kwargs) -> str:
        pregunta = str(kwargs.get("pregunta", ""))
        palabras_pregunta = self._sacar_palabras(pregunta)

        mejor_respuesta = "No encontrado"
        mejores_coincidencias = 0
        for claves, respuesta in self.FAQ.items():
            coincidencias = 0
            for palabra in claves.split():
                if palabra in palabras_pregunta:
                    coincidencias += 1
            if coincidencias > mejores_coincidencias:
                mejores_coincidencias = coincidencias
                mejor_respuesta = respuesta
        return mejor_respuesta

    def _sacar_palabras(self, texto):
        # Minúsculas y sin tildes, para que "envío?" coincida con "envio"
        texto = texto.lower().translate(str.maketrans("áéíóú", "aeiou"))
        return re.findall(r"\w+", texto)

class Reloj(Herramienta):
    def __init__(self):
        super().__init__("reloj", "Dice la fecha y la hora actuales")

    def ejecutar(self, **kwargs) -> str:
        return datetime.now().strftime("%d/%m/%Y %H:%M")
