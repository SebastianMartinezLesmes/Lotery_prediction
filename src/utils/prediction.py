import os
import time
import warnings
import json
from datetime import datetime
import pandas as pd
import joblib
import numpy as np

from src.excel.read_excel import obtener_loterias_disponibles
from openpyxl import load_workbook
from src.core.config import settings
from src.utils.training import entrenar_modelos_por_loteria

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
    
    if len(df_loteria) < 10:
        print(f"⚠️  Datos insuficientes para {loteria}: {len(df_loteria)} registros")
        return
    
    # Cargar modelos
    nombre_archivo = loteria.replace(" ", "_").lower()
    modelo_result_path = os.path.join(CARPETA_MODELOS, f"modelo_result_{nombre_archivo}.pkl")
    modelo_series_path = os.path.join(CARPETA_MODELOS, f"modelo_series_{nombre_archivo}.pkl")

    if not os.path.exists(modelo_result_path) or not os.path.exists(modelo_series_path):
        print(f"📚 Modelos no encontrados para {loteria}, entrenando...")
        X = df_loteria[["dia", "mes", "anio", "dia_semana"]]
        y_result = df_loteria["result"]
        y_series = df_loteria["series"]
        entrenar_modelos_por_loteria(X, y_result, y_series, loteria, min_acc=0.7, max_iter=3000, verbose=True)

    modelo_result = joblib.load(modelo_result_path)
    modelo_series = joblib.load(modelo_series_path)

    # Detectar número de features que espera el modelo
    try:
        n_features = modelo_result.n_features_in_
    except AttributeError:
        # Si no tiene n_features_in_, asumir 4 (modelo básico)
        n_features = 4
    
    # Generar features según lo que espera el modelo
    if n_features == 4:
        # Modelo básico: solo features temporales
        hoy = datetime.today()
        X_hoy = pd.DataFrame([{
            "dia": hoy.day,
            "mes": hoy.month,
            "anio": hoy.year,
            "dia_semana": hoy.weekday()
        }])
    else:
        # Modelo avanzado: generar todas las features
        X_hoy = generar_features_avanzadas(df_loteria)
        
        # Asegurar que tenemos exactamente las features que el modelo espera
        # Rellenar con 0 las features faltantes
        for i in range(n_features):
            col_name = f"feature_{i}"
            if col_name not in X_hoy.columns and len(X_hoy.columns) < n_features:
                X_hoy[col_name] = 0
        
        # Si tenemos más columnas de las necesarias, tomar solo las primeras n_features
        if len(X_hoy.columns) > n_features:
            X_hoy = X_hoy.iloc[:, :n_features]
        elif len(X_hoy.columns) < n_features:
            # Rellenar con 0 hasta completar
            for i in range(len(X_hoy.columns), n_features):
                X_hoy[f"feature_{i}"] = 0

    # Realizar predicción
    numero = modelo_result.predict(X_hoy)[0]
    simbolo_codificado = modelo_series.predict(X_hoy)[0]
    simbolo = obtener_zodiaco(simbolo_codificado)

    print(f"\n>> {loteria}:")
    print(f"   Número: {str(numero).zfill(4)}")
    print(f"   Símbolo: {simbolo}")

    guardar_resultado({
        "loteria": loteria,
        "numero": str(numero).zfill(4),
        "simbolo": str(simbolo).zfill(3)
    }, modelo_usado=f"modelo_result_{nombre_archivo}.pkl", confianza=None)
    duracion = time.time() - inicio
    os.makedirs("logs", exist_ok=True)
    with open(TIEMPOS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{loteria} | Tiempo: {duracion:.2f} s | Predicción completada\n")

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