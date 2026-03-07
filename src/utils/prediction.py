import os
import time
import json
import joblib
import warnings
import numpy as np
import pandas as pd

from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from src.core.config import settings
from src.utils.training import entrenar_modelos_por_loteria
from src.excel.read_excel import obtener_loterias_disponibles

ARCHIVO_EXCEL = str(settings.get_excel_path())
TIEMPOS_LOG = str(settings.LOGS_DIR / "tiempos.log")
CARPETA_MODELOS = str(settings.MODELS_DIR)

warnings.filterwarnings("ignore")

# Mapeo de códigos a signos zodiacales
ZODIACO = [
    "ARI", "TAU", "GEM", "CAN",
    "LEO", "VIR", "LIB", "ESC",
    "SAG", "CAP", "ACU", "PIS"
]

def obtener_zodiaco(codigo):
    """Convierte código numérico a signo zodiacal (abreviación de 3 letras)."""
    try:
        return ZODIACO[int(codigo)]
    except:
        return str(codigo)


def buscar_modelo(loteria, tipo):
    carpeta = Path(settings.MODELS_DIR)
    loteria = loteria.lower().replace(" ", "_")

    patrones = [
        f"1_{loteria}_{tipo}.pkl",
        f"2_{loteria}_{tipo}.pkl"
    ]

    modelos = []

    for p in patrones:
        ruta = carpeta / p
        if ruta.exists():
            modelos.append(ruta)

    if not modelos:
        return None

    # usar el más reciente
    modelos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return modelos[0]

def guardar_resultado(prediccion, modelo_usado=None, confianza=None):
    """
    Guarda la predicción en formato JSON dentro de data/results.json
    
    Args:
        prediccion: El resultado predicho (dict o str)
        modelo_usado: El modelo que generó la predicción
        confianza: Nivel de confianza (si aplica)
    """
    data_dir = settings.DATA_DIR
    output_file = data_dir / "results.json"
    
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "resultado": prediccion,
        "modelo": modelo_usado,
        "confianza": confianza
    }
    
    # Leer resultados anteriores si existen
    datos = []
    if output_file.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except json.JSONDecodeError:
            pass
    
    datos.append(entrada)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def cargar_datos_excel():
    """Carga datos desde el archivo Excel."""
    if not os.path.exists(ARCHIVO_EXCEL):
        print("ERROR: Archivo Excel no encontrado.")
        return pd.DataFrame()

    wb = load_workbook(ARCHIVO_EXCEL, read_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value is not None]

    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        fila = dict(zip(headers, row))
        if all(k in fila and fila[k] is not None for k in ['fecha', 'lottery', 'result', 'series']):
            try:
                fecha = fila['fecha']
                if isinstance(fecha, str):
                    fecha = datetime.strptime(fecha, "%Y-%m-%d")
                result = int(fila['result'])
                series = str(fila['series'])

                data.append({
                    "fecha": fecha,
                    "lottery": fila['lottery'],
                    "result": result,
                    "series": series
                })
            except Exception:
                pass
    return pd.DataFrame(data)


def generar_features_avanzadas(df, fecha_prediccion=None):
    """
    Genera features avanzadas para predicción.
    Compatible con modelos entrenados con feature engineering.
    
    Args:
        df: DataFrame con datos históricos
        fecha_prediccion: Fecha para la cual predecir (default: hoy)
    
    Returns:
        DataFrame con features generadas
    """
    if fecha_prediccion is None:
        fecha_prediccion = datetime.today()
    
    # Features básicas
    features = {
        "dia": fecha_prediccion.day,
        "mes": fecha_prediccion.month,
        "anio": fecha_prediccion.year,
        "dia_semana": fecha_prediccion.weekday()
    }
    
    # Si hay datos históricos, generar features avanzadas
    if len(df) > 0:
        # Ordenar por fecha
        df = df.sort_values("fecha")
        
        # Features de lag (últimos valores)
        if len(df) >= 1:
            features["result_lag_1"] = df["result"].iloc[-1]
        if len(df) >= 2:
            features["result_lag_2"] = df["result"].iloc[-2]
        if len(df) >= 3:
            features["result_lag_3"] = df["result"].iloc[-3]
        
        # Features de rolling (promedios móviles)
        if len(df) >= 7:
            features["result_rolling_mean_7"] = df["result"].iloc[-7:].mean()
            features["result_rolling_std_7"] = df["result"].iloc[-7:].std()
        
        if len(df) >= 30:
            features["result_rolling_mean_30"] = df["result"].iloc[-30:].mean()
            features["result_rolling_std_30"] = df["result"].iloc[-30:].std()
        
        # Features de tendencia
        if len(df) >= 7:
            ultimos_7 = df["result"].iloc[-7:].values
            features["tendencia_7"] = 1 if ultimos_7[-1] > ultimos_7[0] else 0
        
        # Features de frecuencia
        if len(df) >= 30:
            ultimos_30 = df["result"].iloc[-30:]
            features["result_freq_mean"] = ultimos_30.mean()
            features["result_freq_std"] = ultimos_30.std()
        
        # Features temporales adicionales
        features["dia_mes"] = fecha_prediccion.day
        features["semana_anio"] = fecha_prediccion.isocalendar()[1]
        features["trimestre"] = (fecha_prediccion.month - 1) // 3 + 1
        features["es_fin_semana"] = 1 if fecha_prediccion.weekday() >= 5 else 0
        features["es_inicio_mes"] = 1 if fecha_prediccion.day <= 7 else 0
        features["es_fin_mes"] = 1 if fecha_prediccion.day >= 23 else 0
    
    return pd.DataFrame([features])


def preparar_datos(df, loteria):
    """Prepara datos para una lotería específica."""
    df = df[df["lottery"].str.upper() == loteria.upper()]
    df = df.sort_values("fecha")
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    return df


def predecir_para_loteria(df, loteria):
    """
    Genera predicción para una lotería específica.
    Compatible con modelos básicos y avanzados.
    """
    inicio = time.time()

    # Preparar datos históricos
    df_loteria = preparar_datos(df, loteria)

    if len(df_loteria) < settings.TRAINING_CONFIGURE["min_records"]:
        print(f"⚠️  Datos insuficientes para {loteria}: {len(df_loteria)} registros")
        return

    # Rutas de modelos
    modelo_result_path = buscar_modelo(loteria, "result")
    modelo_series_path = buscar_modelo(loteria, "series")

    modelo_result = None
    modelo_series = None

    # =========================
    # Verificar si existen modelos
    # =========================

    if modelo_result_path and modelo_series_path:

        print(f"✓ Modelos encontrados para {loteria}")

        payload_result = joblib.load(str(modelo_result_path))
        payload_series = joblib.load(str(modelo_series_path))

        # extraer modelo real
        modelo_result = payload_result["model"] if isinstance(payload_result, dict) else payload_result
        modelo_series = payload_series["model"] if isinstance(payload_series, dict) else payload_series
        
        # Si el modelo está guardado dentro de un dict
        if isinstance(modelo_result, dict):
            modelo_result = modelo_result["model"]

        if isinstance(modelo_series, dict):
            modelo_series = modelo_series["model"]

    else:

        print(f"📚 Modelos no encontrados para {loteria}, iniciando entrenamiento...")

        X = df_loteria[["dia", "mes", "anio", "dia_semana"]]
        y_result = df_loteria["result"]
        y_series = df_loteria["series"]

        entrenar_modelos_por_loteria(
            X,
            y_result,
            y_series,
            loteria,
            min_acc=settings.TRAINING_CONFIGURE["min_accuracy"],
            max_iter=settings.TRAINING_CONFIGURE["max_iterations"],
            verbose=True 
        )

        # buscar nuevamente después del entrenamiento
        modelo_result_path = buscar_modelo(loteria, "result")
        modelo_series_path = buscar_modelo(loteria, "series")

        if not modelo_result_path or not modelo_series_path:
            raise RuntimeError("Los modelos no se generaron correctamente.")

        print("✓ Modelos generados correctamente, cargando...")

        payload_result = joblib.load(str(modelo_result_path))
        payload_series = joblib.load(str(modelo_series_path))

        modelo_result = payload_result["model"]
        modelo_series = payload_series["model"]

    # =========================
    # Generar features
    # =========================
    features = generar_features_avanzadas(df_loteria)

    # Asegurar columnas compatibles con el modelo
    if hasattr(modelo_result, "feature_names_in_"):
        columnas_modelo = modelo_result.feature_names_in_
        features = features.reindex(columns=columnas_modelo, fill_value=0)

    # =========================
    # Predicción
    # =========================
    pred_result = modelo_result.predict(features)[0]
    pred_series = modelo_series.predict(features)[0]

    # Confianza si el modelo lo soporta
    confianza = None
    if hasattr(modelo_result, "predict_proba"):
        confianza = np.max(modelo_result.predict_proba(features))

    signo = obtener_zodiaco(pred_series)

    resultado_final = {
        "loteria": loteria,
        "numero": int(pred_result),
        "serie": signo
    }

    print("\n🎯 PREDICCIÓN")
    print(f"Lotería: {loteria}")
    print(f"Número: {pred_result}")
    print(f"Signo : {signo}")

    if confianza:
        print(f"Confianza modelo: {confianza:.2%}")

    # Guardar resultado
    guardar_resultado(
        resultado_final,
        modelo_usado="RandomForest",
        confianza=float(confianza) if confianza else None
    )

    # Log de tiempo
    duracion = time.time() - inicio
    with open(TIEMPOS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {loteria} | {duracion:.2f}s\n")

    print(f"⏱ Tiempo de predicción: {duracion:.2f}s")

def main():
    df = cargar_datos_excel()
    if df.empty:
        print("!! No se pudieron cargar datos del archivo.")
        return

    loterias = obtener_loterias_disponibles()
    print(f"\nLoterías detectadas: {loterias}")

    for loteria in loterias:
        print(f"\n>> Procesando: {loteria}")
        df_loteria = preparar_datos(df, loteria)
        if not df_loteria.empty:
            predecir_para_loteria(df_loteria, loteria)
        else:
            print(f"!! No hay suficientes datos para {loteria}")

if __name__ == "__main__":
    main()