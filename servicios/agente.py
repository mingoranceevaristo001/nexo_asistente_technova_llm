import time

from dominio.excepciones import ArgumentosInvalidos, HerramientaNoEncontrada
from dominio.mensaje import Conversacion, Mensaje


class Agente:
    """Bucle del agente: pregunta -> modelo -> herramienta -> respuesta."""

    MAX_VUELTAS = 3  # Para evitar bucles infinitos

    def __init__(self, modelo, herramientas, registro_uso=None):
        self.modelo = modelo
        self._herramientas = {h.nombre: h for h in herramientas}  # Diccionario por nombre
        self._registro = registro_uso  # Nivel 2 (puede ser None)
        self.conversacion = Conversacion()
        # Herramientas usadas en el último procesar(), para que el chat las pueda mostrar
        self.llamadas_herramientas = []

    def procesar(self, texto_usuario) -> str:
        self.llamadas_herramientas = []
        self.conversacion.agregar(Mensaje("usuario", texto_usuario))

        for vuelta in range(self.MAX_VUELTAS):
            respuesta = self.modelo.responder(
                self.conversacion, list(self._herramientas.values())
            )

            # Respuesta normal: se guarda y se devuelve
            if not respuesta.es_llamada_herramienta():
                self.conversacion.agregar(Mensaje("asistente", respuesta.texto))
                return respuesta.texto

            # El modelo pide una herramienta: la ejecutamos y guardamos el resultado
            resultado = self._ejecutar_herramienta(respuesta.herramienta, respuesta.argumentos)
            self.conversacion.agregar(Mensaje("herramienta", resultado))

        # Se han gastado las tres vueltas sin una respuesta final
        texto = "Lo siento, no he conseguido terminar la respuesta."
        self.conversacion.agregar(Mensaje("asistente", texto))
        return texto

    def _ejecutar_herramienta(self, nombre, argumentos):
        if nombre not in self._herramientas:
            raise HerramientaNoEncontrada(f"La herramienta '{nombre}' no existe")

        texto_argumentos = ", ".join(f"{clave}={valor!r}" for clave, valor in argumentos.items())
        self.llamadas_herramientas.append(f"{nombre}({texto_argumentos})")

        exito = True
        inicio = time.perf_counter()
        try:
            # Polimorfismo: no sabemos qué herramienta es, solo que tiene ejecutar()
            resultado = self._herramientas[nombre].ejecutar(**argumentos)
        except ArgumentosInvalidos as error:
            exito = False
            resultado = f"Error: {error}"
        milisegundos = round((time.perf_counter() - inicio) * 1000, 2)

        if self._registro is not None:
            self._registro.registrar(nombre, argumentos, exito, milisegundos)
        return resultado

    def listar_herramientas(self) -> list[str]:
        return [str(herramienta) for herramienta in self._herramientas.values()]

    def cambiar_modelo(self, modelo):
        self.modelo = modelo

    def nueva_conversacion(self):
        self.conversacion = Conversacion()

    def resumen_uso(self):
        # Lo usa el chat para /stats sin tocar el registro directamente
        if self._registro is None:
            return {"usos": {}, "fallos": 0}
        return self._registro.resumen()
