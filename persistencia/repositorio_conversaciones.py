import json
import os

from dominio.mensaje import Conversacion


class RepositorioConversaciones:
    """Guarda y carga conversaciones como archivos JSON."""

    def __init__(self, carpeta="datos/conversaciones"):
        self.carpeta = carpeta

    def _ruta(self, id_conv):
        return os.path.join(self.carpeta, f"{id_conv}.json")

    def guardar(self, conversacion):
        os.makedirs(self.carpeta, exist_ok=True)
        with open(self._ruta(conversacion.id), "w", encoding="utf-8") as archivo:
            json.dump(conversacion.to_dict(), archivo, ensure_ascii=False, indent=2)

    def cargar(self, id_conv) -> Conversacion:
        with open(self._ruta(id_conv), "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        return Conversacion.from_dict(datos)

    def eliminar(self, id_conv):
        os.remove(self._ruta(id_conv))

    def listar(self) -> list[str]:
        if not os.path.exists(self.carpeta):
            return []
        ids = []
        for nombre_archivo in sorted(os.listdir(self.carpeta)):
            if nombre_archivo.endswith(".json"):
                ids.append(os.path.splitext(nombre_archivo)[0])
        return ids
