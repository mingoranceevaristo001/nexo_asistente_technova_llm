import json
import queue
import re
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from dominio.excepciones import ErrorAgente
from dominio.modelos import ModeloEco, ModeloReglas
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from servicios.agente import Agente
from servicios.modelo_llm import ModeloLLM


def crear_app(agente=None, repositorio=None):
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).resolve().parents[1] / "sprites"),
        static_url_path="/sprites",
    )
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    app.extensions["nexo_agente"] = agente
    app.extensions["nexo_repositorio"] = repositorio or RepositorioConversaciones()
    bloqueo = threading.Lock()

    def obtener_agente():
        return app.extensions["nexo_agente"]

    def obtener_repositorio():
        return app.extensions["nexo_repositorio"]

    def guardar_conversacion_actual():
        agente_actual = obtener_agente()
        if len(agente_actual.conversacion):
            obtener_repositorio().guardar(agente_actual.conversacion)

    def serializar_historial():
        return [
            {
                "role": "user" if mensaje.rol == "usuario" else "assistant",
                "content": mensaje.contenido,
            }
            for mensaje in obtener_agente().conversacion.get_mensajes()
            if mensaje.rol in ("usuario", "asistente")
        ]

    @app.get("/")
    def inicio():
        return render_template("chat.html")

    @app.get("/api/historial")
    def historial():
        with bloqueo:
            return jsonify({"messages": serializar_historial()})

    @app.get("/api/conversaciones")
    def conversaciones():
        with bloqueo:
            repositorio = obtener_repositorio()
            ids = repositorio.listar()
            conversaciones_guardadas = []
            for id_conv in ids:
                conversacion = repositorio.cargar(id_conv)
                mensajes_usuario = [
                    mensaje.contenido
                    for mensaje in conversacion.get_mensajes()
                    if mensaje.rol == "usuario"
                ]
                ruta = Path(repositorio.carpeta) / f"{id_conv}.json"
                conversaciones_guardadas.append(
                    {
                        "id": id_conv,
                        "title": (mensajes_usuario[0].strip() if mensajes_usuario else "Chat nuevo"),
                        "updated": ruta.stat().st_mtime,
                        "active": id_conv == obtener_agente().conversacion.id,
                    }
                )
            conversaciones_guardadas.sort(
                key=lambda conversacion: conversacion["updated"],
                reverse=True,
            )
        return jsonify({"conversations": conversaciones_guardadas})

    @app.get("/api/herramientas")
    def herramientas():
        with bloqueo:
            lista = obtener_agente().listar_herramientas()
        return jsonify({"tools": lista})

    @app.post("/api/nueva")
    def nueva_conversacion():
        with bloqueo:
            try:
                guardar_conversacion_actual()
            except OSError:
                app.logger.exception("No se pudo guardar la conversación actual")
                return jsonify({"error": "No se pudo guardar el chat actual."}), 500
            obtener_agente().nueva_conversacion()
            id_actual = obtener_agente().conversacion.id
        return jsonify({"ok": True, "id": id_actual})

    @app.post("/api/conversaciones/<id_conv>")
    def cargar_conversacion(id_conv):
        if re.fullmatch(r"[a-f0-9]{8}", id_conv) is None:
            return jsonify({"error": "Identificador de conversación no válido."}), 400

        with bloqueo:
            repositorio = obtener_repositorio()
            if id_conv not in repositorio.listar():
                return jsonify({"error": "No se encontró esa conversación."}), 404
            try:
                guardar_conversacion_actual()
                conversacion = repositorio.cargar(id_conv)
            except OSError:
                app.logger.exception("No se pudo cargar la conversación %s", id_conv)
                return jsonify({"error": "No se pudo cargar la conversación."}), 500
            obtener_agente().conversacion = conversacion
        return jsonify({"ok": True, "id": id_conv})

    @app.delete("/api/conversaciones/<id_conv>")
    def eliminar_conversacion(id_conv):
        if re.fullmatch(r"[a-f0-9]{8}", id_conv) is None:
            return jsonify({"error": "Identificador de conversación no válido."}), 400

        with bloqueo:
            repositorio = obtener_repositorio()
            if id_conv not in repositorio.listar():
                return jsonify({"error": "No se encontró esa conversación."}), 404
            agente_actual = obtener_agente()
            es_actual = id_conv == agente_actual.conversacion.id
            try:
                repositorio.eliminar(id_conv)
            except OSError:
                app.logger.exception("No se pudo eliminar la conversación %s", id_conv)
                return jsonify({"error": "No se pudo eliminar la conversación."}), 500
            if es_actual:
                agente_actual.nueva_conversacion()
        return jsonify({"ok": True, "active": es_actual})

    @app.post("/api/modelo")
    def cambiar_modelo():
        datos = request.get_json(silent=True)
        nombre = datos.get("name") if isinstance(datos, dict) else None
        modelos = {"reglas": ModeloReglas, "eco": ModeloEco}

        try:
            if nombre == "llm":
                modelo = ModeloLLM()
            elif nombre in modelos:
                modelo = modelos[nombre]()
            else:
                return jsonify({"error": "Modelo no válido."}), 400
        except ErrorAgente as error:
            return jsonify({"error": str(error)}), 400

        with bloqueo:
            obtener_agente().cambiar_modelo(modelo)
        return jsonify({"name": nombre, "label": modelo.nombre})

    @app.post("/api/chat")
    def chat():
        datos = request.get_json(silent=True)
        texto = datos.get("message") if isinstance(datos, dict) else None
        if not isinstance(texto, str) or not texto.strip():
            return jsonify({"error": "Escribe un mensaje antes de enviarlo."}), 400

        eventos = queue.Queue()
        final = object()

        def procesar():
            with bloqueo:
                agente_actual = obtener_agente()
                modelo = agente_actual.modelo
                callback_anterior = None
                if isinstance(modelo, ModeloLLM):
                    callback_anterior = modelo.on_chunk
                    modelo.on_chunk = lambda fragmento: eventos.put(
                        {"type": "chunk", "text": fragmento}
                    )

                try:
                    respuesta = agente_actual.procesar(texto.strip())
                    obtener_repositorio().guardar(agente_actual.conversacion)
                    eventos.put(
                        {
                            "type": "done",
                            "text": respuesta,
                            "tools": list(agente_actual.llamadas_herramientas),
                        }
                    )
                except ErrorAgente as error:
                    eventos.put({"type": "error", "message": str(error)})
                except OSError:
                    app.logger.exception("No se pudo guardar la conversación")
                    eventos.put(
                        {
                            "type": "error",
                            "message": "No se pudo guardar la conversación en disco.",
                        }
                    )
                except Exception:
                    app.logger.exception("Error inesperado procesando un mensaje del chat")
                    eventos.put(
                        {
                            "type": "error",
                            "message": "Se produjo un error inesperado al procesar el mensaje.",
                        }
                    )
                finally:
                    if isinstance(modelo, ModeloLLM):
                        modelo.on_chunk = callback_anterior
                    eventos.put(final)

        def emitir_eventos():
            threading.Thread(target=procesar, daemon=True).start()
            while True:
                evento = eventos.get()
                if evento is final:
                    break
                yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(emitir_eventos()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def crear_agente():
    from dominio.herramientas import BuscadorFAQ, Calculadora, ConversorMoneda, Reloj
    from persistencia.registro_uso import RegistroUso

    herramientas = [Calculadora(), ConversorMoneda(), BuscadorFAQ(), Reloj()]
    return Agente(ModeloReglas(), herramientas, RegistroUso("datos/uso.csv"))
