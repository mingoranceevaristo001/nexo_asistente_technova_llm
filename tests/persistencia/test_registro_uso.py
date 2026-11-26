import csv
from datetime import datetime

from persistencia.registro_uso import RegistroUso


def test_resumen_sin_archivo_no_tiene_usos_ni_fallos(tmp_path):
    registro = RegistroUso(str(tmp_path / "uso.csv"))

    assert registro.resumen() == {"usos": {}, "fallos": 0}


def test_registrar_crea_csv_con_cabecera_y_resumen_correcto(tmp_path):
    ruta = tmp_path / "datos" / "uso.csv"
    registro = RegistroUso(str(ruta))
    registro.registrar("calculadora", {"a": 3, "b": 4}, True, 1.25)
    registro.registrar("calculadora", {"a": 1, "b": 0}, False, 0.5)
    registro.registrar("reloj", {}, True, 0.1)

    with ruta.open("r", newline="", encoding="utf-8") as archivo:
        filas = list(csv.reader(archivo))

    assert filas[0] == RegistroUso.CABECERA
    assert len(filas) == 4
    assert datetime.fromisoformat(filas[1][0])
    assert filas[1][1:] == ["calculadora", "{'a': 3, 'b': 4}", "True", "1.25"]
    assert registro.resumen() == {
        "usos": {"calculadora": 2, "reloj": 1},
        "fallos": 1,
    }


def test_registrar_sin_directorio_en_la_ruta_crea_el_archivo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    registro = RegistroUso("uso.csv")

    registro.registrar("reloj", {}, True, 0)

    assert registro.resumen() == {"usos": {"reloj": 1}, "fallos": 0}
