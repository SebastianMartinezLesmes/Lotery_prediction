import os
import sys
import joblib
import warnings
import numpy as np
import pandas as pd

from sklearn.metrics import (accuracy_score, f1_score, classification_report)
from sklearn.utils.class_weight import compute_class_weight
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import clone
from src.core.config import settings
from src.utils.alerts import check_model_performance
from src.utils.mutation import entrenamiento_evolutivo
from src.utils.training_visualizer import TrainingVisualizer
from src.utils.save_training import (guardar_modelo_si_mejora, crear_base_modelos_IA)


ITERATIONS = settings.TRAINING_CONFIGURE["iterations"]
MIN_ACCURACY = settings.TRAINING_CONFIGURE["min_accuracy"]

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

def entrenar_modelos_por_loteria(X, y_result, y_series, nombre_loteria, min_acc=MIN_ACCURACY , max_iter=ITERATIONS, verbose=False):

    # Entrenar los modelos con rutas específicas para esta lotería
    mejor_modelo_result, mejor_modelo_series, acc_result, acc_series, intentos, history = entrenar_modelos(
        X=X,
        y_result=y_result,
        y_series=y_series,
        min_acc=settings.TRAINING_CONFIGURE["min_accuracy"],
        max_iter=settings.TRAINING_CONFIGURE["max_iterations"],
        verbose=verbose,
        save_models=True,
        enable_visualization=True,
        lottery_name=nombre_loteria
    )

    if verbose:
        print(f"Modelos entrenados para {nombre_loteria.title()} con precision:")
        print(f"   - Result: {acc_result:.4f}")
        print(f"   - Series: {acc_series:.4f}")
    
    # Verificar alertas de rendimiento
    # Obtener F1-scores del historial si están disponibles
    f1_result = history["result_f1"][-1] if history["result_f1"] else None
    f1_series = history["series_f1"][-1] if history["series_f1"] else None
    
    check_model_performance(nombre_loteria, "result", acc_result, f1_result)
    check_model_performance(nombre_loteria, "series", acc_series, f1_series)


def calcular_class_weights(y):
    """
    Calcula pesos balanceados manualmente para evitar warnings con warm_start.
    """
    clases = np.unique(y)
    pesos = compute_class_weight(
        class_weight="balanced",
        classes=clases,
        y=y
    )
    return dict(zip(clases, pesos))

def entrenar_modelo_result(X_train, y_train, random_state, warm_start_model=None):
    """
    Entrena modelo para predecir números.
    Si se proporciona warm_start_model, continúa desde ese modelo.
    """

    class_weights = calcular_class_weights(y_train)

    if warm_start_model is not None:
        modelo = clone(warm_start_model)

        modelo.n_estimators += 50
        modelo.warm_start = True
        modelo.class_weight = class_weights

        modelo.fit(X_train, y_train)

        modelo.warm_start = False
    else:
        modelo = RandomForestClassifier(
            n_estimators=200,
            max_depth=4,
            min_samples_split=5,
            class_weight=class_weights,
            random_state=random_state
        )

        modelo.fit(X_train, y_train)
    return modelo

def entrenar_modelo_series(X_train, y_train, random_state=42, warm_start_model=None):
    """
    Entrena modelo para predecir signos zodiacales.
    Si se proporciona warm_start_model, continúa desde ese modelo.
    """

    class_weights = calcular_class_weights(y_train)

    if warm_start_model is not None:
        modelo = clone(warm_start_model)

        modelo.n_estimators += 50
        modelo.warm_start = True
        modelo.class_weight = class_weights

        modelo.fit(X_train, y_train)

        modelo.warm_start = False
    else:
        modelo = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            class_weight=class_weights,
            random_state=random_state
        )

        modelo.fit(X_train, y_train)
    return modelo

def cargar_mejor_modelo(nombre_loteria: str, tipo_modelo: str):
    """
    Carga el mejor modelo disponible según accuracy.
    """

    base = crear_base_modelos_IA(nombre_loteria)
    paths = base[tipo_modelo]

    mejor_modelo = None
    mejor_acc = -1

    for path in paths:

        if not os.path.exists(path):
            continue

        try:
            payload = joblib.load(path)

            acc = payload.get("accuracy", 0)

            if acc > mejor_acc:
                mejor_acc = acc
                mejor_modelo = payload["model"]

        except Exception:
            continue

    return mejor_modelo, mejor_acc

def entrenar_modelos(
    X,
    y_result, y_series,
    min_acc=settings.TRAINING_CONFIGURE["min_accuracy"],
    max_iter=settings.TRAINING_CONFIGURE["iterations"],
    verbose=False,
    save_models=True,
    enable_visualization=True,
    lottery_name="unknown"
):
    mejor_acc_result = 0
    mejor_acc_series = 0
    mejor_modelo_result = None
    mejor_modelo_series = None

    # ==============================
    # Inicializar visualizador
    # ==============================
    visualizer = None
    if enable_visualization and verbose:
        visualizer = TrainingVisualizer(
            lottery_name=lottery_name,
            total_iterations=max_iter,
            enable_progress_bar=True,
            enable_logging=True
        )

    history = {
        "attempts": [],
        "result_acc": [],
        "series_acc": [],
        "result_f1": [],
        "series_f1": []
    }

    # ==============================
    # Cargar modelos previos (Memoria IA)
    # ==============================
    modelos_cargados = False
    modelo_base_result = None
    modelo_base_series = None

    if save_models:

        modelo_cargado, acc = cargar_mejor_modelo(
            lottery_name,
            "result"
        )

        if modelo_cargado:
            mejor_modelo_result = modelo_cargado
            mejor_acc_result = acc
            modelo_base_result = modelo_cargado
            modelos_cargados = True

            if verbose:
                print(f"✓ Modelo Result cargado (baseline: {acc:.4f})")
                print("  Continuará entrenando desde memoria IA...")

        modelo_cargado, acc = cargar_mejor_modelo(
            lottery_name,
            "series"
        )

        if modelo_cargado:
            mejor_modelo_series = modelo_cargado
            mejor_acc_series = acc
            modelo_base_series = modelo_cargado
            modelos_cargados = True

            if verbose:
                print(f"✓ Modelo Series cargado (baseline: {acc:.4f})")
                print("  Continuará entrenando desde memoria IA...")

    # ==============================
    # Información si ya superan umbral
    # ==============================
    if modelos_cargados and \
       mejor_acc_result >= min_acc and \
       mejor_acc_series >= min_acc:

        if verbose:
            print(f"\n✓ Modelos existentes superan el umbral:")
            print(f"  Result: {mejor_acc_result:.4f} >= {min_acc}")
            print(f"  Series: {mejor_acc_series:.4f} >= {min_acc}")
            print(f"\n  Entrenando {max_iter} iteraciones para mejorar...\n")

    # ==============================
    # Loop de entrenamiento
    # ==============================
    for intento in range(1, max_iter + 1):

        random_state = np.random.randint(0, 10000)

        X_train, X_test, \
        y_train_result, y_test_result, \
        y_train_series, y_test_series = train_test_split(
            X,
            y_result,
            y_series,
            test_size=0.2,
            random_state=random_state
        )

        modelo_result, acc_result = entrenamiento_evolutivo(
            X_train,
            y_train_result,
            X_test,
            y_test_result,
            generaciones=10,
            poblacion_size=10
        )

        modelo_series, acc_series = entrenamiento_evolutivo(
            X_train,
            y_train_series,
            X_test,
            y_test_series,
            generaciones=10,
            poblacion_size=10
        )

        acc_result, f1_result = evaluar_y_reportar(
            modelo_result,
            X_test,
            y_test_result,
            "Result",
            verbose=False
        )

        acc_series, f1_series = evaluar_y_reportar(
            modelo_series,
            X_test,
            y_test_series,
            "Series",
            verbose=False
        )

        history["attempts"].append(intento)
        history["result_acc"].append(acc_result)
        history["series_acc"].append(acc_series)
        history["result_f1"].append(f1_result)
        history["series_f1"].append(f1_series)

        # ==============================
        # Visualización
        # ==============================
        if visualizer:
            visualizer.update(
                intento,
                acc_result,
                acc_series,
                f1_result,
                f1_series
            )
        elif verbose:
            sys.stdout.write(
                f"\r🔄 Intento {intento}/{max_iter}"
                f" | Acc Result: {acc_result:.4f}"
                f" | Series: {acc_series:.4f}"
                f" | F1 Result: {f1_result:.4f}"
                f" | Series: {f1_series:.4f}"
            )
            sys.stdout.flush()

        # ==============================
        # Mejor modelo encontrado
        # ==============================
        if acc_result > mejor_acc_result:
            mejor_acc_result = acc_result
            mejor_modelo_result = modelo_result

        if acc_series > mejor_acc_series:
            mejor_acc_series = acc_series
            mejor_modelo_series = modelo_series

        # ==============================
        # Early stop inteligente (convergencia real)
        # ==============================
        if (
            acc_result >= min_acc and
            acc_series >= min_acc and
            intento >= 5
        ):

            recent_result = history["result_acc"][-50:]
            recent_series = history["series_acc"][-50:]

            if (
                len(recent_result) == 50 and
                max(recent_result) - min(recent_result) < 0.002 and
                max(recent_series) - min(recent_series) < 0.002
            ):
                if visualizer:
                    visualizer.finish(success=True)
                elif verbose:
                    print(f"\nEarly stop por convergencia (intento {intento})")

                break

    # ==============================
    # Finalizar visualización
    # ==============================
    if visualizer and intento == max_iter:
        visualizer.finish(success=False)

    # ==============================
    # Guardado en Memoria IA
    # ==============================
    if save_models:

        if not visualizer:
            print("\n🧠 Actualizando memoria IA:")

        try:

            guardar_modelo_si_mejora(
                nombre_loteria=lottery_name,
                tipo_modelo="result",
                modelo=mejor_modelo_result,
                accuracy=mejor_acc_result,
            )

            guardar_modelo_si_mejora(
                nombre_loteria=lottery_name,
                tipo_modelo="series",
                modelo=mejor_modelo_series,
                accuracy=mejor_acc_series,
            )

        except Exception as e:
            print(f"❌ Error al guardar modelos: {e}")

    return (
        mejor_modelo_result,
        mejor_modelo_series,
        mejor_acc_result,
        mejor_acc_series,
        intento,
        history
    )

if __name__ == "__main__":
    print("🚀 Ejecutando entrenamiento con datos reales desde 'data/resultados_astro.xlsx'...\n")


    # Ruta absoluta al archivo Excel en data/
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ruta_excel = os.path.join(BASE_DIR, "data", "resultados_astro.xlsx")

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
            min_acc=settings.TRAINING_CONFIGURE["min_accuracy"],
            max_iter=settings.TRAINING_CONFIGURE["iterations"],
            verbose=True
        )

    print("\n\n🏁 Entrenamiento finalizado para todas las loterías.")
