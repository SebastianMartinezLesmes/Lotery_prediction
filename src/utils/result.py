# src/utils/result.py

import os
import json
from datetime import datetime

DATA_DIR = "data"
OUTPUT_FILE = "results.json"

def guardar_resultado(prediccion, modelo_usado=None, confianza=None):
    """
    Guarda la predicción en formato JSON dentro de la carpeta /data/results.json

    Args:
        prediccion (str | dict): El resultado predicho.
        modelo_usado (str, optional): El modelo que generó la predicción.
        confianza (float, optional): Nivel de confianza (si aplica).
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    ruta_salida = os.path.join(DATA_DIR, OUTPUT_FILE)

    entrada = {
        "timestamp": datetime.now().isoformat(),
        "resultado": prediccion,
        "modelo": modelo_usado,
        "confianza": confianza
    }

    # Leer resultados anteriores si existen
    datos = []
    if os.path.exists(ruta_salida):
        with open(ruta_salida, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
            except json.JSONDecodeError:
                pass

    datos.append(entrada)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    print(f"📦 Resultado guardado en {ruta_salida}")
