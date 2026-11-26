import uuid
from datetime import datetime

from dominio.excepciones import LimiteContextoSuperado

LIMITE_TOKENS_CONVERSACION_POR_DEFECTO = 1000


class Mensaje:
    """Un mensaje de la conversación: quién lo dice, qué dice y cuándo."""

    ROLES_VALIDOS = ("usuario", "asistente", "herramienta")

    def __init__(self, rol, contenido):
        if rol not in self.ROLES_VALIDOS:
            raise ValueError(f"Rol no válido: {rol}")
        self.rol = rol
        self.contenido = contenido
        self.fecha = datetime.now().isoformat()

    def __str__(self):
        return f"[{self.rol}] {self.contenido}"

    def to_dict(self):
        return {"rol": self.rol, "contenido": self.contenido, "fecha": self.fecha}

    @classmethod
    def from_dict(cls, datos):
        mensaje = cls(datos["rol"], datos["contenido"])
        mensaje.fecha = datos["fecha"]  # Se conserva la fecha original
        return mensaje


class Conversacion:
    """Lista de mensajes con un límite de tokens."""

    def __init__(self, limite_tokens=LIMITE_TOKENS_CONVERSACION_POR_DEFECTO):
        self.id = uuid.uuid4().hex[:8]
        self.__mensajes = []  # Privado: solo se toca con los métodos de la clase
        self._limite_tokens = limite_tokens  # Protegido

    def agregar(self, mensaje):
        self.__mensajes.append(mensaje)
        if self.tokens_estimados() > self._limite_tokens:
            self.__mensajes.pop()  # El mensaje que no cabe no se queda guardado
            raise LimiteContextoSuperado(
                f"Se ha superado el límite de {self._limite_tokens} tokens"
            )

    def get_mensajes(self):
        # Devuelve una copia para que nadie modifique el historial desde fuera
        return list(self.__mensajes)

    def tokens_estimados(self):
        total_palabras = 0
        for mensaje in self.__mensajes:
            total_palabras += len(mensaje.contenido.split())
        return round(total_palabras * 1.3)

    def __len__(self):
        return len(self.__mensajes)

    def to_dict(self):
        return {
            "id": self.id,
            "mensajes": [mensaje.to_dict() for mensaje in self.__mensajes],
        }

    @classmethod
    def from_dict(cls, datos):
        conversacion = cls()
        conversacion.id = datos["id"]
        for datos_mensaje in datos["mensajes"]:
            conversacion.agregar(Mensaje.from_dict(datos_mensaje))
        return conversacion
