from dominio.excepciones import ErrorAgente, LimiteContextoSuperado
from dominio.modelos import ModeloEco, ModeloReglas
from servicios.modelo_llm import ModeloLLM


class ChatConsola:
    """Capa de presentación: solo lee lo que escribe el usuario y muestra resultados."""

    def __init__(self, agente, repositorio):
        self.agente = agente
        self.repositorio = repositorio
        modelo = getattr(self.agente, "modelo", None)
        if isinstance(modelo, ModeloLLM):
            modelo.on_chunk = self._mostrar_fragmento

    def iniciar(self):
        self._mostrar_bienvenida()

        while True:
            try:
                texto = input("tú > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n¡Hasta pronto!")
                break

            if texto == "":
                continue
            if texto == "/salir":
                print("¡Hasta pronto!")
                break

            # Los errores del agente se muestran, pero el programa no se cierra
            try:
                if texto.startswith("/"):
                    self._ejecutar_comando(texto)
                else:
                    self._enviar_mensaje(texto)
            except LimiteContextoSuperado as error:
                print(f"⚠ {error}. Usa /guardar y /nueva para empezar otra conversación.")
            except ErrorAgente as error:
                print(f"⚠ {error}")

    def _mostrar_bienvenida(self):
        print("╭──────────────────────────────────────╮")
        print("│ 🤖 NEXO · asistente de TechNova      │")
        print("│ Escribe /herramientas o /salir       │")
        print("╰──────────────────────────────────────╯")

    def _enviar_mensaje(self, texto):
        try:
            respuesta = self.agente.procesar(texto)
        except ErrorAgente:
            if getattr(getattr(self.agente, "modelo", None), "transmite_respuesta", False):
                print()
            raise
        for llamada in self.agente.llamadas_herramientas:
            print(f"🔧 {llamada}")
        if getattr(self.agente.modelo, "transmite_respuesta", False):
            print()
        else:
            print(f"NEXO > {respuesta}")

    @staticmethod
    def _mostrar_fragmento(fragmento):
        print(fragmento, end="", flush=True)

    def _ejecutar_comando(self, texto):
        partes = texto.split()
        comando = partes[0]
        argumento = partes[1] if len(partes) > 1 else ""

        if comando == "/herramientas":
            for herramienta in self.agente.listar_herramientas():
                print(herramienta)
        elif comando == "/modelo":
            self._cambiar_modelo(argumento)
        elif comando == "/historial":
            self._mostrar_historial()
        elif comando == "/guardar":
            self._guardar()
        elif comando == "/cargar":
            self._cargar(argumento)
        elif comando == "/lista":
            self._mostrar_lista()
        elif comando == "/nueva":
            self.agente.nueva_conversacion()
            print(f"🆕 Conversación nueva: {self.agente.conversacion.id}")
        elif comando == "/stats":
            self._mostrar_stats()
        else:
            print(f"Comando no reconocido: {comando}. Prueba con /herramientas")

    def _cambiar_modelo(self, nombre):
        if nombre == "eco":
            modelo = ModeloEco()
        elif nombre == "reglas":
            modelo = ModeloReglas()
        elif nombre == "llm":
            modelo = ModeloLLM(on_chunk=self._mostrar_fragmento)
        else:
            print("Uso: /modelo eco, /modelo reglas o /modelo llm")
            return
        self.agente.cambiar_modelo(modelo)
        print(f"✔ Modelo cambiado a {modelo.nombre}")

    def _mostrar_historial(self):
        conversacion = self.agente.conversacion
        if len(conversacion) == 0:
            print("La conversación está vacía.")
        for mensaje in conversacion.get_mensajes():
            print(mensaje)
        print(f"Tokens estimados: {conversacion.tokens_estimados()}")

    def _guardar(self):
        conversacion = self.agente.conversacion
        self.repositorio.guardar(conversacion)
        print(f"💾 Conversación {conversacion.id} guardada")

    def _cargar(self, id_conv):
        if id_conv == "":
            print("Uso: /cargar <id>")
            return
        try:
            conversacion = self.repositorio.cargar(id_conv)
        except FileNotFoundError:
            print(f"No existe ninguna conversación guardada con id {id_conv}")
            return
        self.agente.conversacion = conversacion
        print(f"📂 Conversación {id_conv} cargada ({len(conversacion)} mensajes)")

    def _mostrar_lista(self):
        ids = self.repositorio.listar()
        if not ids:
            print("No hay conversaciones guardadas.")
        for id_conv in ids:
            print(f"- {id_conv}")

    def _mostrar_stats(self):
        resumen = self.agente.resumen_uso()
        if not resumen["usos"]:
            print("Todavía no se ha usado ninguna herramienta.")
            return
        print("📊 Uso de herramientas:")
        for herramienta, veces in resumen["usos"].items():
            print(f"- {herramienta}: {veces}")
        print(f"Fallos: {resumen['fallos']}")
