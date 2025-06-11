import pandas as pd
import numpy as np
from datetime import datetime
from src.excel.read_excel import obtener_loterias_disponibles
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from openpyxl import load_workbook
import os
import warnings
warnings.filterwarnings("ignore")

ARCHIVO_EXCEL = "resultados_astro.xlsx"

def cargar_datos_excel():
    if not os.path.exists(ARCHIVO_EXCEL):
        print("❌ Archivo Excel no encontrado.")
        return pd.DataFrame()

    wb = load_workbook(ARCHIVO_EXCEL, read_only=True)
    ws = wb.active

    headers = [cell.value for cell in ws[1] if cell.value is not None]
    print(f"📌 Encabezados encontrados: {headers}")

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

                # print(f"✔️ Fila válida: Fecha={fecha}, Número={result}, Serie={series}")  

                data.append({
                    "fecha": fecha,
                    "lottery": fila['lottery'],
                    "result": result,
                    "series": series
                })
            except Exception as e:
                pass #print(f"❌ Error procesando fila: {fila} - {e}")  
        else:
            pass # print(f"🔴 Fila inválida: claves faltantes en {fila.keys()}")  

    print(f"✅ Filas cargadas: {len(data)}")
    return pd.DataFrame(data)

def preparar_datos(df, loteria="ASTRO LUNA"):
    df = df[df["lottery"].str.upper() == loteria.upper()]
    df = df.sort_values("fecha")

    # Extraer características del tiempo
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    df = df[["dia", "mes", "anio", "dia_semana", "result", "series"]]
    return df

def entrenar_y_predecir(df):
    X = df[["dia", "mes", "anio", "dia_semana"]]
    y_result = df["result"]
    y_series = df["series"]

    # División para validación
    X_train, X_test, y_train_result, y_test_result = train_test_split(X, y_result, test_size=0.2, random_state=42)
    _, _, y_train_series, y_test_series = train_test_split(X, y_series, test_size=0.2, random_state=42)

    # Modelos
    modelo_result = DecisionTreeClassifier(max_depth=5, random_state=0)
    modelo_series = LogisticRegression(max_iter=1000)

    modelo_result.fit(X_train, y_train_result)
    modelo_series.fit(X_train, y_train_series)

    # Validación simple
    pred_result = modelo_result.predict(X_test)
    pred_series = modelo_series.predict(X_test)

    print(f"📊 Exactitud (número): {accuracy_score(y_test_result, pred_result):.2f}")
    print(f"📊 Exactitud (simbol): {accuracy_score(y_test_series, pred_series):.2f}")

    # Predicción para hoy
    hoy = datetime.today()
    X_hoy = pd.DataFrame([{
        "dia": hoy.day,
        "mes": hoy.month,
        "anio": hoy.year,
        "dia_semana": hoy.weekday()
    }])

    numero_predicho = modelo_result.predict(X_hoy)[0]
    serie_predicha = modelo_series.predict(X_hoy)[0]

    print("\n🔮 Predicción para el próximo sorteo:")
    print(f"   🔢 Número: {str(numero_predicho).zfill(4)}")
    print(f"   🧿 Simbol: {str(serie_predicha).zfill(3)}")

if __name__ == "__main__":
    df = cargar_datos_excel()
    if not df.empty:
        loterias = obtener_loterias_disponibles()
        print(f"\n🎯 Loterías detectadas: {loterias}")

        for loteria in loterias:
            print(f"\n🔮 Predicción para: {loteria}")
            df_loteria = preparar_datos(df, loteria)
            if not df_loteria.empty:
                entrenar_y_predecir(df_loteria)
            else:
                print(f"⚠️ No hay datos suficientes para {loteria}")
    else:
        print("⚠️ No se pudo entrenar el modelo.")

