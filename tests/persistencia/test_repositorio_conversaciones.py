import json

from dominio.mensaje import Conversacion, Mensaje
from persistencia.repositorio_conversaciones import RepositorioConversaciones


def test_guardar_y_cargar_conversacion_conserva_id_y_mensajes(tmp_path):
    repositorio = RepositorioConversaciones(str(tmp_path / "conversaciones"))
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "Hola"))
    conversacion.agregar(Mensaje("asistente", "¡Buenas!"))

    repositorio.guardar(conversacion)
    cargada = repositorio.cargar(conversacion.id)

    assert cargada.to_dict() == conversacion.to_dict()


def test_listar_devuelve_ids_ordenados_y_omite_archivos_que_no_son_json(tmp_path):
    carpeta = tmp_path / "conversaciones"
    carpeta.mkdir()
    (carpeta / "b.json").write_text("{}", encoding="utf-8")
    (carpeta / "a.json").write_text("{}", encoding="utf-8")
    (carpeta / "notas.txt").write_text("no es una conversación", encoding="utf-8")
    (carpeta / "subcarpeta").mkdir()
    repositorio = RepositorioConversaciones(str(carpeta))

    assert repositorio.listar() == ["a", "b"]


def test_listar_devuelve_lista_vacia_si_la_carpeta_no_existe(tmp_path):
    repositorio = RepositorioConversaciones(str(tmp_path / "inexistente"))

    assert repositorio.listar() == []


def test_guardar_escribe_json_legible_en_utf8(tmp_path):
    repositorio = RepositorioConversaciones(str(tmp_path / "conversaciones"))
    conversacion = Conversacion()
    conversacion.agregar(Mensaje("usuario", "¡Hola!"))

    repositorio.guardar(conversacion)

    ruta = tmp_path / "conversaciones" / f"{conversacion.id}.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["mensajes"][0]["contenido"] == "¡Hola!"
