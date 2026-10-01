"""Captura el estado de todas las estaciones de Valenbisi.

Fuente: Geoportal del Ayuntamiento de València (capa 228 de Tráfico), en GeoJSON.
Cada ejecución guarda una fila por estación en datos/AAAA-MM-DD/HHMMSS.csv.gz,
con la hora local de València. Pensado para ejecutarse cada 15 minutos desde
GitHub Actions.

Uso: python recolector/capturar.py [CARPETA_DATOS]
"""
import csv
import gzip
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

URL = (
    "https://geoportal.valencia.es/server/rest/services/OPENDATA/Trafico/MapServer/228/query"
    "?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)
ZONA = ZoneInfo("Europe/Madrid")
COLUMNAS = [
    "momento",            # hora local de la captura
    "estacion_id",
    "nombre",
    "direccion",
    "latitud",
    "longitud",
    "bicis",              # bicis disponibles
    "anclajes_libres",
    "capacidad",          # anclajes totales (bicis + libres puede ser menor: anclajes averiados)
    "abierta",
    "actualizado_fuente", # última actualización de la estación según la fuente
]


def descargar(intentos=3, espera=20):
    """Devuelve la lista de features del GeoJSON. Reintenta si la fuente falla."""
    for intento in range(1, intentos + 1):
        try:
            r = requests.get(URL, timeout=30)
            r.raise_for_status()
            return r.json()["features"]
        except (requests.RequestException, KeyError, ValueError) as e:
            if intento == intentos:
                raise RuntimeError(f"No se pudo descargar tras {intentos} intentos: {e}") from e
            time.sleep(espera)


def a_filas(features, momento):
    """Convierte los features del GeoJSON en filas con las COLUMNAS del CSV."""
    filas = []
    for f in features:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        actualizado = datetime.strptime(p["updated_at"], "%d/%m/%Y %H:%M:%S")
        filas.append({
            "momento": momento.strftime("%Y-%m-%d %H:%M:%S"),
            "estacion_id": p["number"],
            "nombre": p["name"],
            "direccion": p["address"],
            "latitud": round(lat, 6),
            "longitud": round(lon, 6),
            "bicis": p["available"],
            "anclajes_libres": p["free"],
            "capacidad": p["total"],
            "abierta": p["open"] == "T",
            "actualizado_fuente": actualizado.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return filas


def guardar(filas, carpeta, momento):
    """Guarda la captura en datos/AAAA-MM-DD/HHMMSS.csv.gz.

    Un archivo comprimido por captura: git nunca reescribe archivos existentes
    y el repositorio crece poco (unos 8 KB por captura).
    """
    dia = Path(carpeta) / f"{momento:%Y-%m-%d}"
    dia.mkdir(parents=True, exist_ok=True)
    archivo = dia / f"{momento:%H%M%S}.csv.gz"
    with gzip.open(archivo, "wt", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)
    return archivo


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "datos"
    momento = datetime.now(ZONA).replace(tzinfo=None, microsecond=0)
    filas = a_filas(descargar(), momento)
    archivo = guardar(filas, carpeta, momento)
    print(f"{len(filas)} estaciones guardadas en {archivo} ({momento})")


if __name__ == "__main__":
    main()
