from dominio.excepciones import HerramientaNoEncontrada
from dominio.herramientas import Calculadora
from dominio.modelos import ModeloEco, Respuesta
from servicios.agente import Agente


class RegistroFalso:
    def __init__(self):
        self.registros = []

    def registrar(self, herramienta, argumentos, exito, milisegundos):
        self.registros.append((herramienta, argumentos, exito, milisegundos))

    def resumen(self):
        return {"usos": {}, "fallos": 0}


class ModeloHerramientaFalsa:
    def __init__(self, herramienta, argumentos):
        self.herramienta = herramienta
        self.argumentos = argumentos

    def responder(self, conversacion, herramientas):
        if conversacion.get_mensajes()[-1].rol == "herramienta":
            return Respuesta(texto="Operación terminada")
        return Respuesta(
            herramienta=self.herramienta,
            argumentos=self.argumentos,
        )


def test_procesar_guarda_mensaje_de_usuario_y_respuesta_final():
    agente = Agente(ModeloEco(), [])

    respuesta = agente.procesar("Hola")

    assert respuesta == "Has dicho: Hola"
    assert [(mensaje.rol, mensaje.contenido) for mensaje in agente.conversacion.get_mensajes()] == [
        ("usuario", "Hola"),
        ("asistente", "Has dicho: Hola"),
    ]


def test_procesar_ejecuta_herramienta_y_registra_el_uso_correctamente():
    registro = RegistroFalso()
    agente = Agente(
        ModeloHerramientaFalsa("calculadora", {"a": 3, "b": 4, "operacion": "*"}),
        [Calculadora()],
        registro,
    )

    respuesta = agente.procesar("multiplica")

    assert respuesta == "Operación terminada"
    assert agente.llamadas_herramientas == ["calculadora(a=3, b=4, operacion='*')"]
    assert registro.registros[0][:3] == (
        "calculadora",
        {"a": 3, "b": 4, "operacion": "*"},
        True,
    )
    assert [
        (mensaje.rol, mensaje.contenido)
        for mensaje in agente.conversacion.get_mensajes()
    ] == [
        ("usuario", "multiplica"),
        ("herramienta", "3 * 4 = 12"),
        ("asistente", "Operación terminada"),
    ]


def test_procesar_convierte_argumentos_invalidos_en_resultado_de_herramienta():
    registro = RegistroFalso()
    agente = Agente(
        ModeloHerramientaFalsa(
            "calculadora", {"a": 1, "b": 0, "operacion": "/"}
        ),
        [Calculadora()],
        registro,
    )

    assert agente.procesar("divide") == "Operación terminada"

    assert agente.conversacion.get_mensajes()[1].contenido == (
        "Error: no se puede dividir entre 0"
    )
    assert registro.registros[0][2] is False


def test_procesar_lanza_error_si_el_modelo_pide_herramienta_inexistente():
    agente = Agente(ModeloHerramientaFalsa("desconocida", {}), [])

    try:
        agente.procesar("haz algo")
    except HerramientaNoEncontrada as error:
        assert "desconocida" in str(error)
    else:
        raise AssertionError("Se esperaba HerramientaNoEncontrada")


def test_agente_sin_registro_devuelve_resumen_vacio():
    agente = Agente(ModeloEco(), [])

    assert agente.resumen_uso() == {"usos": {}, "fallos": 0}


def test_cambiar_modelo_y_nueva_conversacion_actualizan_el_estado():
    agente = Agente(ModeloEco(), [])
    conversacion_anterior = agente.conversacion
    nuevo_modelo = ModeloEco()
    agente.procesar("Hola")

    agente.cambiar_modelo(nuevo_modelo)
    agente.nueva_conversacion()

    assert agente.modelo is nuevo_modelo
    assert agente.conversacion is not conversacion_anterior
    assert len(agente.conversacion) == 0
