import csv
import gzip
import json
from datetime import datetime
from pathlib import Path

from recolector.capturar import COLUMNAS, a_filas, guardar

MUESTRA = json.loads((Path(__file__).parent / "muestra_geoportal.json").read_text(encoding="utf-8"))
MOMENTO = datetime(2026, 10, 1, 19, 45, 0)


def test_a_filas_convierte_cada_estacion():
    filas = a_filas(MUESTRA["features"], MOMENTO)

    assert len(filas) == len(MUESTRA["features"])
    assert set(filas[0]) == set(COLUMNAS)


def test_a_filas_respeta_coordenadas_y_formatos():
    feature = MUESTRA["features"][0]
    fila = a_filas([feature], MOMENTO)[0]
    lon, lat = feature["geometry"]["coordinates"]

    assert fila["latitud"] == round(lat, 6)
    assert fila["longitud"] == round(lon, 6)
    assert 39 < fila["latitud"] < 40 and -1 < fila["longitud"] < 0  # València
    assert fila["momento"] == "2026-10-01 19:45:00"
    assert fila["estacion_id"] == feature["properties"]["number"]
    assert fila["bicis"] == feature["properties"]["available"]
    assert fila["anclajes_libres"] == feature["properties"]["free"]
    assert fila["abierta"] is (feature["properties"]["open"] == "T")
    datetime.strptime(fila["actualizado_fuente"], "%Y-%m-%d %H:%M:%S")


def test_guardar_escribe_un_csv_comprimido_por_captura(tmp_path):
    filas = a_filas(MUESTRA["features"], MOMENTO)

    archivo = guardar(filas, tmp_path, MOMENTO)

    assert archivo == tmp_path / "2026-10-01" / "194500.csv.gz"
    with gzip.open(archivo, "rt", encoding="utf-8") as f:
        leidas = list(csv.DictReader(f))
    assert len(leidas) == len(filas)
    assert list(leidas[0]) == COLUMNAS


def test_guardar_separa_capturas_y_dias(tmp_path):
    filas = a_filas(MUESTRA["features"], MOMENTO)

    guardar(filas, tmp_path, MOMENTO)
    guardar(filas, tmp_path, datetime(2026, 10, 1, 20, 0, 0))
    guardar(filas, tmp_path, datetime(2026, 10, 2, 0, 0, 0))

    rutas = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*.csv.gz"))
    assert rutas == ["2026-10-01/194500.csv.gz", "2026-10-01/200000.csv.gz", "2026-10-02/000000.csv.gz"]
