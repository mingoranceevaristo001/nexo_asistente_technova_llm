import csv
import os
from datetime import datetime


class RegistroUsoLLM:
    """Registra tokens de salida y coste estimado de cada petición LLM."""

    CABECERA = ["timestamp", "question", "output_tokens", "cost"]
    COSTE_POR_MIL_TOKENS = 0.008

    def __init__(self, ruta="datos/uso_llm.csv"):
        self.ruta = ruta

    def registrar(self, pregunta, tokens_salida):
        carpeta = os.path.dirname(self.ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        archivo_nuevo = not os.path.exists(self.ruta)
        coste = tokens_salida * self.COSTE_POR_MIL_TOKENS / 1000
        with open(self.ruta, "a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if archivo_nuevo:
                escritor.writerow(self.CABECERA)
            escritor.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    pregunta,
                    tokens_salida,
                    f"{coste:.8f}",
                ]
            )
