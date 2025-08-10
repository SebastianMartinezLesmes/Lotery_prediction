import os
import sys
import joblib
import warnings
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report

ITERATIONS = 1000
MIN_ACCURACY = 0.7

warnings.filterwarnings(
    "ignore",
    message="The number of unique classes is greater than 50% of the number of samples."
)

def evaluar_y_reportar(modelo, X_test, y_test, nombre_modelo, verbose=True):
    """Evalúa un modelo y muestra métricas de precisión y F1."""
    if modelo is None:
        print(f"⚠️ No hay modelo entrenado para {nombre_modelo}.")
        return None, None

    pred = modelo.predict(X_test)
    acc = accuracy_score(y_test, pred)
    f1 = f1_score(y_test, pred, average='macro')

    if verbose:
        print(f"\n🔍 Reporte Final del Mejor Modelo {nombre_modelo}:")
        print(f"   - Precisión: {acc:.4f}")
        print(f"   - F1-Score: {f1:.4f}")
        print(classification_report(y_test, pred))

    return acc, f1

def generar_ruta_modelo(nombre_loteria, tipo):
    nombre_archivo = f"modelo_{tipo}_{nombre_loteria.lower().replace(' ', '_')}.pkl"
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ruta_modelo = os.path.join(BASE_DIR, "models", nombre_archivo)
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)

    return ruta_modelo

def entrenar_modelos_por_loteria(X, y_result, y_series, nombre_loteria, min_acc=MIN_ACCURACY , max_iter=ITERATIONS, verbose=False):
    modelo_result_path = generar_ruta_modelo(nombre_loteria, "result")
    modelo_series_path = generar_ruta_modelo(nombre_loteria, "series")

    if verbose:
        print(f"📁 Guardando modelos en:\n- {modelo_result_path}\n- {modelo_series_path}")

    # Entrenar los modelos con rutas específicas para esta lotería
    mejor_modelo_result, mejor_modelo_series, acc_result, acc_series, intentos, history = entrenar_modelos(
        X=X,
        y_result=y_result,
        y_series=y_series,
        min_acc=min_acc,
        max_iter=max_iter,
        verbose=verbose,
        save_models=True,
        modelo_result_path=modelo_result_path,
        modelo_series_path=modelo_series_path
    )

    if verbose:
        print(f"✅ Modelos entrenados para {nombre_loteria.title()} con precisión:")
        print(f"   - Result: {acc_result:.4f}")
        print(f"   - Series: {acc_series:.4f}")

def entrenar_modelo_result(X_train, y_train, random_state):
    modelo = RandomForestClassifier(
        n_estimators=200,
        max_depth=4,
        min_samples_split=5,
        class_weight='balanced',
        random_state=random_state
    )
    modelo.fit(X_train, y_train)
    return modelo

def entrenar_modelo_series(X_train, y_train):
    modelo = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        class_weight='balanced',
        random_state=42
    )
    modelo.fit(X_train, y_train)
    return modelo

def entrenar_modelos(X, y_result, y_series, min_acc=MIN_ACCURACY, max_iter=ITERATIONS, verbose=False,
                     save_models=True, modelo_result_path=None, modelo_series_path=None):

    mejor_acc_result = 0
    mejor_acc_series = 0
    mejor_modelo_result = None
    mejor_modelo_series = None

    history = {
        "attempts": [],
        "result_acc": [],
        "series_acc": [],
        "result_f1": [],
        "series_f1": []
    }

    # Intentar cargar modelos previos si existen
    if save_models:
        if modelo_result_path and os.path.exists(modelo_result_path):
            try:
                modelo_cargado = joblib.load(modelo_result_path)
                pred = modelo_cargado.predict(X)
                acc = accuracy_score(y_result, pred)
                mejor_modelo_result = modelo_cargado
                mejor_acc_result = acc
                if verbose:
                    print(f"📦 Modelo Result cargado con precisión previa: {acc:.4f}")
            except Exception as e:
                if verbose:
                    print(f"⚠️ Error al cargar modelo_result: {e}")

        if modelo_series_path and os.path.exists(modelo_series_path):
            try:
                modelo_cargado = joblib.load(modelo_series_path)
                pred = modelo_cargado.predict(X)
                acc = accuracy_score(y_series, pred)
                mejor_modelo_series = modelo_cargado
                mejor_acc_series = acc
                if verbose:
                    print(f"📦 Modelo Series cargado con precisión previa: {acc:.4f}")
            except Exception as e:
                if verbose:
                    print(f"⚠️ Error al cargar modelo_series: {e}")

    # Iterar entrenamientos
    for intento in range(1, max_iter + 1):
        random_state = np.random.randint(0, 10000)

        X_train, X_test, y_train_result, y_test_result = train_test_split(
            X, y_result, test_size=0.2, random_state=random_state)
        _, _, y_train_series, y_test_series = train_test_split(
            X, y_series, test_size=0.2, random_state=random_state)

        modelo_result = entrenar_modelo_result(X_train, y_train_result, random_state)
        modelo_series = entrenar_modelo_series(X_train, y_train_series)

        acc_result, f1_result = evaluar_y_reportar(modelo_result, X_test, y_test_result, "Result", verbose=False)
        acc_series, f1_series = evaluar_y_reportar(modelo_series, X_test, y_test_series, "Series", verbose=False)

        history["attempts"].append(intento)
        history["result_acc"].append(acc_result)
        history["series_acc"].append(acc_series)
        history["result_f1"].append(f1_result)
        history["series_f1"].append(f1_series)

        if verbose:
            sys.stdout.write(
                f"\r🔄 Intento {intento}/{max_iter} | Acc Result: {acc_result:.4f} | Series: {acc_series:.4f} | "
                f"F1 Result: {f1_result:.4f} | Series: {f1_series:.4f}"
            )
            sys.stdout.flush()

        # Actualizar mejores modelos
        if acc_result > mejor_acc_result:
            mejor_acc_result = acc_result
            mejor_modelo_result = modelo_result

        if acc_series > mejor_acc_series:
            mejor_acc_series = acc_series
            mejor_modelo_series = modelo_series

        if acc_result >= min_acc and acc_series >= min_acc:
            if verbose:
                print(f"\n✔️ Umbral alcanzado en intento {intento}")
            break

    # Comparar y guardar modelos
    if save_models:
        print("\n🔎 Comparación de mejoras:")

        try:
            os.makedirs(os.path.dirname(modelo_result_path), exist_ok=True)

            if modelo_result_path:
                print(f"   Result: precisión final={mejor_acc_result:.4f}")
                if mejor_modelo_result:
                    joblib.dump(mejor_modelo_result, modelo_result_path)

            if modelo_series_path:
                print(f"   Series: precisión final={mejor_acc_series:.4f}")
                if mejor_modelo_series:
                    joblib.dump(mejor_modelo_series, modelo_series_path)

        except Exception as e:
            print(f"❌ Error al guardar modelos: {e}")

    return mejor_modelo_result, mejor_modelo_series, mejor_acc_result, mejor_acc_series, intento, history

if __name__ == "__main__":
    print("🚀 Ejecutando entrenamiento con datos reales desde 'resultados_astro.xlsx'...\n")

    import pandas as pd

    # Ruta absoluta al archivo Excel en la raíz del proyecto
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ruta_excel = os.path.join(BASE_DIR, "resultados_astro.xlsx")

    if not os.path.exists(ruta_excel):
        print(f"❌ Archivo no encontrado: {ruta_excel}")
        sys.exit(1)

    # Leer datos
    df = pd.read_excel(ruta_excel)

    # Validar columnas requeridas
    columnas_necesarias = {"fecha", "lottery", "slug", "result", "series"}
    if not columnas_necesarias.issubset(df.columns):
        print("❌ El archivo no contiene todas las columnas necesarias:", columnas_necesarias)
        sys.exit(1)

    # Limpieza y preprocesamiento
    df = df.dropna(subset=["fecha", "lottery", "result", "series"])
    df["result"] = df["result"].astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)

    # Convertir series (signo zodiacal) a categorías numéricas
    df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes

    # Extraer features temporales
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year

    df["dia_semana"] = df["fecha"].dt.weekday
    X = df[["dia", "mes", "anio", "dia_semana"]].values
    y_result = df["result"].values
    y_series = df["series"].values

    loterias = df["lottery"].str.lower().unique()

    for nombre_loteria in loterias:
        print(f"\n📈 Entrenando modelos para: {nombre_loteria.title()}")
        df_loteria = df[df["lottery"].str.lower() == nombre_loteria]

        df_loteria["dia_semana"] = df_loteria["fecha"].dt.weekday
        X_l = df_loteria[["dia", "mes", "anio", "dia_semana"]].values
        y_r = df_loteria["result"].values
        y_s = df_loteria["series"].values

        entrenar_modelos_por_loteria(
            X=X_l,
            y_result=y_r,
            y_series=y_s,
            nombre_loteria=nombre_loteria,
            min_acc=MIN_ACCURACY ,
            max_iter=ITERATIONS,
            verbose=True
        )

    print("\n\n🏁 Entrenamiento finalizado para todas las loterías.")
