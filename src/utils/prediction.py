import os
import time
import warnings
from datetime import datetime
from src.utils.result import guardar_resultado
from src.excel.read_excel import obtener_loterias_disponibles
from src.utils.entrenamiento import entrenar_modelos_por_loteria
from openpyxl import load_workbook
import pandas as pd
import joblib
from src.utils.config import ARCHIVO_EXCEL, TIEMPOS_LOG, CARPETA_MODELOS
from src.excel.read_excel import obtener_loterias_disponibles
from src.utils.result import guardar_resultado
from src.utils.zodiaco import obtener_zodiaco
from src.utils.training import entrenar_modelos_por_loteria

warnings.filterwarnings("ignore")

def cargar_datos_excel():
    if not os.path.exists(ARCHIVO_EXCEL):
        print("❌ Archivo Excel no encontrado.")
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

def preparar_datos(df, loteria):
    df = df[df["lottery"].str.upper() == loteria.upper()]
    df = df.sort_values("fecha")
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    return df[["dia", "mes", "anio", "dia_semana", "result", "series"]]

def predecir_para_loteria(df, loteria):
    inicio = time.time()
    X = df[["dia", "mes", "anio", "dia_semana"]]
    y_result = df["result"]
    y_series = df["series"]

    nombre_archivo = loteria.replace(" ", "_").lower()
    modelo_result_path = os.path.join(CARPETA_MODELOS, f"modelo_result_{nombre_archivo}.pkl")
    modelo_series_path = os.path.join(CARPETA_MODELOS, f"modelo_series_{nombre_archivo}.pkl")

    if not os.path.exists(modelo_result_path) or not os.path.exists(modelo_series_path):
        print(f"📚 Modelos no encontrados para {loteria}, entrenando...")
        entrenar_modelos_por_loteria(X, y_result, y_series, loteria, min_acc=0.7, max_iter=3000, verbose=True)

    modelo_result = joblib.load(modelo_result_path)
    modelo_series = joblib.load(modelo_series_path)

    hoy = datetime.today()
    X_hoy = pd.DataFrame([{
        "dia": hoy.day,
        "mes": hoy.month,
        "anio": hoy.year,
        "dia_semana": hoy.weekday()
    }])

    numero = modelo_result.predict(X_hoy)[0]
    simbolo_codificado = modelo_series.predict(X_hoy)[0]
    simbolo = obtener_zodiaco(simbolo_codificado)


    print(f"\n🎰 {loteria}:")
    print(f"   🔢 Número: {str(numero).zfill(4)}")
    print(f"   🧿 Símbolo: {simbolo}")

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
        print("⚠️ No se pudieron cargar datos del archivo.")
        return

    loterias = obtener_loterias_disponibles()
    print(f"\n🎯 Loterías detectadas: {loterias}")

    for loteria in loterias:
        print(f"\n🔮 Procesando: {loteria}")
        df_loteria = preparar_datos(df, loteria)
        if not df_loteria.empty:
            predecir_para_loteria(df_loteria, loteria)
        else:
            print(f"⚠️ No hay suficientes datos para {loteria}")

if __name__ == "__main__":
    main()