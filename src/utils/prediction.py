import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.result import guardar_resultado
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

                data.append({
                    "fecha": fecha,
                    "lottery": fila['lottery'],
                    "result": result,
                    "series": series
                })
            except Exception as e:
                pass  # Error procesando fila
        else:
            pass  # Fila incompleta

    print(f"✅ Filas cargadas: {len(data)}")
    return pd.DataFrame(data)

def preparar_datos(df, loteria="ASTRO LUNA"):
    df = df[df["lottery"].str.upper() == loteria.upper()]
    df = df.sort_values("fecha")

    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    df = df[["dia", "mes", "anio", "dia_semana", "result", "series"]]
    return df

def entrenar_y_predecir(df, min_acc=0.5, max_intentos=3000):
    X = df[["dia", "mes", "anio", "dia_semana"]]
    y_result = df["result"]
    y_series = df["series"]

    mejor_acc_result = 0
    mejor_acc_series = 0
    mejor_modelo_result = None
    mejor_modelo_series = None

    for intento in range(1, max_intentos + 1):
        print(f"🔁 Intento {intento}/{max_intentos}", end="\r")
        random_state = np.random.randint(0, 10000)

        X_train, X_test, y_train_result, y_test_result = train_test_split(
            X, y_result, test_size=0.2, random_state=random_state)
        _, _, y_train_series, y_test_series = train_test_split(
            X, y_series, test_size=0.2, random_state=random_state)

        modelo_result = DecisionTreeClassifier(max_depth=5, random_state=random_state)
        modelo_series = LogisticRegression(max_iter=1000)

        modelo_result.fit(X_train, y_train_result)
        modelo_series.fit(X_train, y_train_series)

        pred_result = modelo_result.predict(X_test)
        pred_series = modelo_series.predict(X_test)

        acc_result = accuracy_score(y_test_result, pred_result)
        acc_series = accuracy_score(y_test_series, pred_series)

        if acc_result > mejor_acc_result or acc_series > mejor_acc_series:
            mejor_acc_result = acc_result
            mejor_acc_series = acc_series
            mejor_modelo_result = modelo_result
            mejor_modelo_series = modelo_series

        if acc_result >= min_acc and acc_series >= min_acc:
            print(f"✅ Exactitud mínima alcanzada en intento {intento}")
            break

    print(f"📊 Exactitud (número): {mejor_acc_result:.2f}")
    print(f"📊 Exactitud (simbol): {mejor_acc_series:.2f}")

    # Predicción para hoy
    hoy = datetime.today()
    X_hoy = pd.DataFrame([{
        "dia": hoy.day,
        "mes": hoy.month,
        "anio": hoy.year,
        "dia_semana": hoy.weekday()
    }])

    numero_predicho = mejor_modelo_result.predict(X_hoy)[0]
    serie_predicha = mejor_modelo_series.predict(X_hoy)[0]

    print("\n🔮 Predicción para el próximo sorteo:")
    print(f"   🔢 Número: {str(numero_predicho).zfill(4)}")
    print(f"   🧿 Simbol: {str(serie_predicha).zfill(3)}")

    resultado = {
        "loteria": loteria,
        "numero": str(numero_predicho).zfill(4),
        "simbolo": str(serie_predicha).zfill(3),
    }
    guardar_resultado(resultado, modelo_usado="DecisionTree + LogisticRegression",
        confianza=(mejor_acc_result + mejor_acc_series) / 2)

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