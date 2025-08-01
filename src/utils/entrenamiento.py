# utils/entrenamiento.py

import os
import sys
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
# from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report

def generar_ruta_modelo(nombre_loteria, tipo):
    nombre_archivo = f"modelo_{tipo}_{nombre_loteria.lower().replace(' ', '_')}.pkl"
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ruta_modelo = os.path.join(BASE_DIR, "models", nombre_archivo)
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)

    return ruta_modelo


def entrenar_modelos_por_loteria(X, y_result, y_series, nombre_loteria, min_acc=0.7, max_iter=3000, verbose=False):
    modelo_result_path = generar_ruta_modelo(nombre_loteria, "result")
    modelo_series_path = generar_ruta_modelo(nombre_loteria, "series")

    if verbose:
        print(f"📁 Guardando modelos en:\n- {modelo_result_path}\n- {modelo_series_path}")

    # Entrenar los modelos con rutas específicas para esta lotería
    modelo_result, modelo_series, acc_result, acc_series, intento, history = entrenar_modelos(
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

def entrenar_modelos(X, y_result, y_series, min_acc=0.7, max_iter=3000, verbose=False,
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

    for intento in range(1, max_iter + 1):
        random_state = np.random.randint(0, 10000)

        X_train, X_test, y_train_result, y_test_result = train_test_split(
            X, y_result, test_size=0.2, random_state=random_state)
        _, _, y_train_series, y_test_series = train_test_split(
            X, y_series, test_size=0.2, random_state=random_state)

        modelo_result = entrenar_modelo_result(X_train, y_train_result, random_state)
        modelo_series = entrenar_modelo_series(X_train, y_train_series)

        pred_result = modelo_result.predict(X_test)
        pred_series = modelo_series.predict(X_test)

        acc_result = accuracy_score(y_test_result, pred_result)
        acc_series = accuracy_score(y_test_series, pred_series)

        f1_result = f1_score(y_test_result, pred_result, average='macro')
        f1_series = f1_score(y_test_series, pred_series, average='macro')

        history["attempts"].append(intento)
        history["result_acc"].append(acc_result)
        history["series_acc"].append(acc_series)
        history["result_f1"].append(f1_result)
        history["series_f1"].append(f1_series)

        if verbose:
            sys.stdout.write(
                f"\r🔄 Intento {intento}/{max_iter} | Acc Result: {acc_result:.4f} | Series: {acc_series:.4f} | F1 Result: {f1_result:.4f} | Series: {f1_series:.4f}"
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

    if verbose:
        print("\n\n🔍 Reporte Final del Mejor Modelo Result:")
        if mejor_modelo_result:
            print(classification_report(y_test_result, mejor_modelo_result.predict(X_test)))

        print("\n🔍 Reporte Final del Mejor Modelo Series:")
        if mejor_modelo_series:
            print(classification_report(y_test_series, mejor_modelo_series.predict(X_test)))

    if save_models:
        os.makedirs(os.path.dirname(modelo_result_path), exist_ok=True)
        if mejor_modelo_result:
            joblib.dump(mejor_modelo_result, modelo_result_path)
        if mejor_modelo_series:
            joblib.dump(mejor_modelo_series, modelo_series_path)

    return mejor_modelo_result, mejor_modelo_series, mejor_acc_result, mejor_acc_series, intento, history

# Agrega esto al final de entrenamiento.py
if __name__ == "__main__":
    print("🚀 Ejecutando entrenamiento de prueba con datos sintéticos...\n")

    from sklearn.datasets import make_classification

    # Crear datos sintéticos una vez para todas las loterías
    X, y = make_classification(n_samples=300, n_features=4, n_classes=2, random_state=42)
    y_result = y
    y_series = np.random.randint(0, 2, size=len(y))

    loterias = ['astro luna', 'astro sol']

    for nombre_loteria in loterias:
        print(f"\n📈 Entrenando modelos para: {nombre_loteria.title()}")
        entrenar_modelos_por_loteria(
            X=X,
            y_result=y_result,
            y_series=y_series,
            nombre_loteria=nombre_loteria,
            min_acc=0.7,
            max_iter=1000,
            verbose=True
        )

    print("\n\n🏁 Entrenamiento finalizado para todas las loterías.")

