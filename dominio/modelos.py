import re


class Respuesta:
    def __init__(self, texto=None, herramienta=None, argumentos=None):
        self.texto = texto  # Respuesta final para el usuario
        self.herramienta = herramienta  # O bien: nombre de la herramienta a usar
        self.argumentos = argumentos or {}

    def es_llamada_herramienta(self) -> bool:
        return self.herramienta is not None


class Modelo:
    """Clase base de todos los modelos."""

    transmite_respuesta = False

    def __init__(self, nombre):
        self.nombre = nombre

    def responder(self, conversacion, herramientas) -> Respuesta:
        raise NotImplementedError("Cada modelo debe implementar responder()")


class ModeloEco(Modelo):
    """Repite lo último que ha dicho el usuario. Sirve para probar que todo encaja."""

    def __init__(self):
        super().__init__("ModeloEco")

    def responder(self, conversacion, herramientas) -> Respuesta:
        ultimo_texto = ""
        for mensaje in conversacion.get_mensajes():
            if mensaje.rol == "usuario":
                ultimo_texto = mensaje.contenido
        return Respuesta(texto=f"Has dicho: {ultimo_texto}")


class ModeloReglas(Modelo):
    """Modelo simulado: decide qué hacer siguiendo reglas sencillas."""

    # Palabra que puede escribir el usuario -> código de moneda
    MONEDAS = {
        "eur": "EUR", "euros": "EUR",
        "usd": "USD", "dólares": "USD", "dolares": "USD",
        "gbp": "GBP", "libras": "GBP",
        "jpy": "JPY", "yenes": "JPY",
    }
    RELOJ = ["hora", "fecha", "día", "dia"]
    PALABRAS_FAQ = ["envío", "envio", "devolver", "devolución", "devolucion", "horario", "pago"]
    SALUDOS = ["hola", "buenas", "buenos", "hey"]
    # Frase con la que se contesta cuando la herramienta ya ha dado su resultado
    FRASES = {
        "calculadora": "El resultado es {}. ¿Necesitas algo más?",
        "conversor_moneda": "{}.",
        "buscador_faq": "Según nuestra información: {}",
        "reloj": "Ahora mismo es {}.",
    }

    def __init__(self):
        super().__init__("ModeloReglas")
        self._herramienta_pedida = None  # Para saber cómo contestar cuando llegue el resultado

    def responder(self, conversacion, herramientas) -> Respuesta:
        ultimo = conversacion.get_mensajes()[-1]

        # Regla 1: si el último mensaje es de una herramienta, damos la respuesta final
        if ultimo.rol == "herramienta":
            return self._responder_con_resultado(ultimo.contenido)

        # Resto de reglas, en orden. La primera que encaje decide la respuesta
        reglas = [
            self._regla_calculadora,
            self._regla_conversor,
            self._regla_faq,
            self._regla_reloj,
            self._regla_saludo,
        ]
        for regla in reglas:
            respuesta = regla(ultimo.contenido)
            if respuesta is not None:
                self._herramienta_pedida = respuesta.herramienta
                return respuesta

        return Respuesta(texto="No estoy seguro, ¿puedes reformularlo?")

    def _responder_con_resultado(self, resultado):
        if resultado.startswith("Error"):
            return Respuesta(texto=f"Lo siento, no he podido hacerlo. {resultado}")
        if resultado == "No encontrado":
            return Respuesta(
                texto="Lo siento, no he encontrado nada sobre eso. ¿Puedes reformularlo?"
            )
        frase = self.FRASES.get(self._herramienta_pedida, "Aquí tienes: {}")
        return Respuesta(texto=frase.format(resultado))

    def _regla_calculadora(self, texto):
        # Busca algo como "3 * 79.9" (la x también vale como multiplicar)
        encontrado = re.search(r"(\d+[.,]?\d*)\s*([+\-*/x])\s*(\d+[.,]?\d*)", texto.lower())
        if encontrado is None:
            return None
        a, operacion, b = encontrado.groups()
        if operacion == "x":
            operacion = "*"
        argumentos = {"a": self._a_numero(a), "b": self._a_numero(b), "operacion": operacion}
        return Respuesta(herramienta="calculadora", argumentos=argumentos)

    def _regla_reloj(self, texto):
        palabras = re.findall(r"\w+", texto.lower())
        for fecha in self.RELOJ:
            if fecha in palabras:
                return Respuesta(herramienta="reloj")
        return None


    def _regla_conversor(self, texto):
        # Monedas que aparecen en el texto, en orden: la primera es el origen y la segunda el destino
        monedas = []
        for palabra in re.findall(r"\w+", texto.lower()):
            if palabra in self.MONEDAS:
                monedas.append(self.MONEDAS[palabra])

        # Solo se pide el conversor si aparece USD, GBP o JPY (o sus nombres)
        monedas_extranjeras = [moneda for moneda in monedas if moneda != "EUR"]
        if not monedas_extranjeras:
            return None

        origen = monedas[0]
        destino = monedas[1] if len(monedas) > 1 else "EUR"

        numero = re.search(r"\d+[.,]?\d*", texto)
        cantidad = self._a_numero(numero.group()) if numero else None

        argumentos = {"cantidad": cantidad, "origen": origen, "destino": destino}
        return Respuesta(herramienta="conversor_moneda", argumentos=argumentos)

    def _regla_faq(self, texto):
        minusculas = texto.lower()
        for palabra in self.PALABRAS_FAQ:
            if palabra in minusculas:
                return Respuesta(herramienta="buscador_faq", argumentos={"pregunta": texto})
        return None

    def _regla_saludo(self, texto):
        palabras = re.findall(r"\w+", texto.lower())
        for saludo in self.SALUDOS:
            if saludo in palabras:
                return Respuesta(texto="¡Hola! Soy NEXO, ¿en qué te ayudo?")
        return None

    def _a_numero(self, texto):
        # "79,9" -> 79.9 y "3" -> 3 (entero si no tiene decimales)
        numero = float(texto.replace(",", "."))
        if numero.is_integer():
            return int(numero)
        return numero
