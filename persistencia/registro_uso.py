import csv
import os
from datetime import datetime


class RegistroUso:
    """Guarda en un CSV cada vez que se ejecuta una herramienta."""

    CABECERA = ["fecha", "herramienta", "argumentos", "exito", "milisegundos"]

    def __init__(self, ruta="datos/uso.csv"):
        self.ruta = ruta

    def registrar(self, herramienta, argumentos, exito, milisegundos):
        carpeta = os.path.dirname(self.ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        archivo_nuevo = not os.path.exists(self.ruta)
        with open(self.ruta, "a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if archivo_nuevo:
                escritor.writerow(self.CABECERA)  # La cabecera solo se escribe una vez
            fecha = datetime.now().isoformat(timespec="seconds")
            escritor.writerow([fecha, herramienta, argumentos, exito, milisegundos])

    def resumen(self) -> dict:
        usos = {}
        fallos = 0
        if os.path.exists(self.ruta):
            with open(self.ruta, "r", newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    herramienta = fila["herramienta"]
                    usos[herramienta] = usos.get(herramienta, 0) + 1
                    if fila["exito"] != "True":
                        fallos += 1
        return {"usos": usos, "fallos": fallos}
