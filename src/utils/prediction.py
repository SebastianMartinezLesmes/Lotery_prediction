import os
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from src.excel.read_excel import obtener_loterias_disponibles

warnings.filterwarnings("ignore")

ARCHIVO_EXCEL = "resultados_astro.xlsx"
COLUMNAS_REQUERIDAS = ['fecha', 'lottery', 'result', 'series']

def cargar_datos_excel():
    if not os.path.exists(ARCHIVO_EXCEL):
        print("❌ Archivo Excel no encontrado.")
        return pd.DataFrame()

    wb = load_workbook(ARCHIVO_EXCEL, read_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1] if cell.value]

    print(f"📌 Encabezados encontrados: {headers}")
    data = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        fila = dict(zip(headers, row))
        if not all(k in fila and fila[k] is not None for k in COLUMNAS_REQUERIDAS):
            continue

        try:
            fecha = datetime.strptime(fila['fecha'], "%Y-%m-%d") if isinstance(fila['fecha'], str) else fila['fecha']
            data.append({
                "fecha": fecha,
                "lottery": fila['lottery'],
                "result": int(fila['result']),
                "series": str(fila['series'])
            })
        except Exception:
            continue  

    print(f"✅ Filas cargadas: {len(data)}")
    return pd.DataFrame(data)

def preparar_datos(df, loteria="ASTRO LUNA"):
    df = df[df["lottery"].str.upper() == loteria.upper()].sort_values("fecha")
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    return df[["dia", "mes", "anio", "dia_semana", "result", "series"]]

def entrenar_modelos(df, min_acc=0.5, max_intentos=3000):
    X = df[["dia", "mes", "anio", "dia_semana"]]
    y_result = df["result"]
    y_series = df["series"]

    mejor_modelo_result = mejor_modelo_series = None
    mejor_acc_result = mejor_acc_series = 0

    for intento in range(1, max_intentos + 1):
        print(f"🔁 Intento {intento}/{max_intentos}", end="\r")
        seed = np.random.randint(0, 10000)

        X_train, X_test, y_train_result, y_test_result = train_test_split(X, y_result, test_size=0.2, random_state=seed)
        _, _, y_train_series, y_test_series = train_test_split(X, y_series, test_size=0.2, random_state=seed)

        modelo_result = DecisionTreeClassifier(max_depth=5, random_state=seed)
        modelo_series = LogisticRegression(max_iter=1000)

        modelo_result.fit(X_train, y_train_result)
        modelo_series.fit(X_train, y_train_series)

        acc_result = accuracy_score(y_test_result, modelo_result.predict(X_test))
        acc_series = accuracy_score(y_test_series, modelo_series.predict(X_test))

        if acc_result > mejor_acc_result:
            mejor_acc_result = acc_result
            mejor_modelo_result = modelo_result
        if acc_series > mejor_acc_series:
            mejor_acc_series = acc_series
            mejor_modelo_series = modelo_series

        if acc_result >= min_acc and acc_series >= min_acc:
            print(f"✅ Exactitud mínima alcanzada en intento {intento}")
            break

    return mejor_modelo_result, mejor_modelo_series, mejor_acc_result, mejor_acc_series

def predecir_siguiente(modelo_result, modelo_series):
    hoy = datetime.today()
    X_hoy = pd.DataFrame([{
        "dia": hoy.day,
        "mes": hoy.month,
        "anio": hoy.year,
        "dia_semana": hoy.weekday()
    }])

    numero_predicho = modelo_result.predict(X_hoy)[0]
    serie_predicha = modelo_series.predict(X_hoy)[0]

    return numero_predicho, serie_predicha

def mostrar_resultados(acc_result, acc_series, numero, serie):
    print(f"📊 Exactitud (número): {acc_result:.2f}")
    print(f"📊 Exactitud (simbol): {acc_series:.2f}")
    print("\n🔮 Predicción para el próximo sorteo:")
    print(f"   🔢 Número: {str(numero).zfill(4)}")
    print(f"   🧿 Simbol: {str(serie).zfill(3)}")

if __name__ == "__main__":
    df = cargar_datos_excel()

    if df.empty:
        print("⚠️ No se pudo entrenar el modelo.")
    else:
        loterias = obtener_loterias_disponibles()
        print(f"\n🎯 Loterías detectadas: {loterias}")

        for loteria in loterias:
            print(f"\n🔮 Predicción para: {loteria}")
            df_loteria = preparar_datos(df, loteria)
            if df_loteria.empty:
                print(f"⚠️ No hay datos suficientes para {loteria}")
                continue

            modelo_result, modelo_series, acc_result, acc_series = entrenar_modelos(df_loteria)

            if modelo_result and modelo_series:
                numero, serie = predecir_siguiente(modelo_result, modelo_series)
                mostrar_resultados(acc_result, acc_series, numero, serie)
            else:
                print("⚠️ No se pudo generar un modelo confiable.")
