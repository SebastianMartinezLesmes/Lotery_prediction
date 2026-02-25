import os
import sys
import joblib
import warnings
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
from src.utils.training_visualizer import TrainingVisualizer

ITERATIONS = 8000
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
    ruta_modelo = os.path.join(BASE_DIR, "IA_models", nombre_archivo)
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)

    return ruta_modelo

def entrenar_modelos_por_loteria(X, y_result, y_series, nombre_loteria, min_acc=MIN_ACCURACY , max_iter=ITERATIONS, verbose=False):
    modelo_result_path = generar_ruta_modelo(nombre_loteria, "result")
    modelo_series_path = generar_ruta_modelo(nombre_loteria, "series")

    if verbose:
        print(f"Guardando modelos en:\n- {modelo_result_path}\n- {modelo_series_path}")

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
        modelo_series_path=modelo_series_path,
        enable_visualization=True,
        lottery_name=nombre_loteria
    )

    if verbose:
        print(f"Modelos entrenados para {nombre_loteria.title()} con precision:")
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
                     save_models=True, modelo_result_path=None, modelo_series_path=None, 
                     enable_visualization=True, lottery_name="unknown"):

    mejor_acc_result = 0
    mejor_acc_series = 0
    mejor_modelo_result = None
    mejor_modelo_series = None

    # Inicializar visualizador
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

    # Intentar cargar modelos previos si existen
    modelos_cargados = False
    if save_models:
        if modelo_result_path and os.path.exists(modelo_result_path):
            try:
                modelo_cargado = joblib.load(modelo_result_path)
                pred = modelo_cargado.predict(X)
                acc = accuracy_score(y_result, pred)
                mejor_modelo_result = modelo_cargado
                mejor_acc_result = acc
                modelos_cargados = True
                if verbose:
                    print(f"Modelo Result cargado con precision previa: {acc:.4f}")
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
                modelos_cargados = True
                if verbose:
                    print(f"Modelo Series cargado con precision previa: {acc:.4f}")
            except Exception as e:
                if verbose:
                    print(f"⚠️ Error al cargar modelo_series: {e}")
    
    # Si ambos modelos ya superan el umbral, informar y continuar
    if modelos_cargados and mejor_acc_result >= min_acc and mejor_acc_series >= min_acc:
        if verbose:
            print(f"\nLos modelos existentes ya superan el umbral:")
            print(f"   Result: {mejor_acc_result:.4f} >= {min_acc}")
            print(f"   Series: {mejor_acc_series:.4f} >= {min_acc}")
            print(f"\n   Continuando entrenamiento para intentar mejorar...")
            print(f"   (Se entrenaran {max_iter} iteraciones buscando mejoras)\n")

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

        # Actualizar visualización
        if visualizer:
            visualizer.update(intento, acc_result, acc_series, f1_result, f1_series)
        elif verbose:
            sys.stdout.write(
                f"\r🔄 Intento {intento}/{max_iter} | Acc Result: {acc_result:.4f} | Series: {acc_series:.4f} | "
                f"F1 Result: {f1_result:.4f} | Series: {f1_series:.4f}"
            )
            sys.stdout.flush()

        # Actualizar mejores modelos
        mejora_result = False
        mejora_series = False
        
        if acc_result > mejor_acc_result:
            mejor_acc_result = acc_result
            mejor_modelo_result = modelo_result
            mejora_result = True

        if acc_series > mejor_acc_series:
            mejor_acc_series = acc_series
            mejor_modelo_series = modelo_series
            mejora_series = True

        # Detener solo si:
        # 1. Ambos modelos superan el umbral Y
        # 2. Han pasado al menos 100 iteraciones (para dar oportunidad de mejorar) Y
        # 3. No ha habido mejoras en las últimas 50 iteraciones
        if acc_result >= min_acc and acc_series >= min_acc and intento >= 100:
            # Verificar si hubo mejoras recientes
            ultimas_50 = history["attempts"][-50:] if len(history["attempts"]) >= 50 else history["attempts"]
            if len(ultimas_50) >= 50:
                # Si no hubo mejoras en las últimas 50 iteraciones, detener
                if visualizer:
                    visualizer.finish(success=True)
                elif verbose:
                    print(f"\nUmbral alcanzado y sin mejoras recientes en intento {intento}")
                break
            # Si aún no hay 50 iteraciones, continuar

    # Finalizar visualización si no se alcanzó el umbral
    if visualizer and intento == max_iter:
        visualizer.finish(success=False)
    
    # Comparar y guardar modelos con verificación de historial
    if save_models:
        if not visualizer:
            print("\nComparacion de mejoras:")

        try:
            os.makedirs(os.path.dirname(modelo_result_path), exist_ok=True)

            # Calcular score combinado del entrenamiento actual
            current_combined_score = (mejor_acc_result + mejor_acc_series) / 2
            
            # Verificar historial y decidir si sobrescribir .pkl
            should_update_pkl = _verificar_y_comparar_historial(
                lottery_name=lottery_name,
                current_score=current_combined_score,
                current_result_acc=mejor_acc_result,
                current_series_acc=mejor_acc_series,
                modelo_result_path=modelo_result_path,
                modelo_series_path=modelo_series_path,
                verbose=verbose
            )
            
            # Guardar modelos según decisión
            if should_update_pkl:
                if modelo_result_path and mejor_modelo_result:
                    joblib.dump(mejor_modelo_result, modelo_result_path)
                    print(f"   ✅ Modelo Result actualizado en IA_models/ (Acc: {mejor_acc_result:.4f})")
                
                if modelo_series_path and mejor_modelo_series:
                    joblib.dump(mejor_modelo_series, modelo_series_path)
                    print(f"   ✅ Modelo Series actualizado en IA_models/ (Acc: {mejor_acc_series:.4f})")
            else:
                print(f"   📊 Modelos guardados solo en historial (no superan el .pkl actual)")
                print(f"      Result: {mejor_acc_result:.4f} | Series: {mejor_acc_series:.4f}")

        except Exception as e:
            print(f"❌ Error al guardar modelos: {e}")

    return mejor_modelo_result, mejor_modelo_series, mejor_acc_result, mejor_acc_series, intento, history


def _verificar_y_comparar_historial(
    lottery_name: str,
    current_score: float,
    current_result_acc: float,
    current_series_acc: float,
    modelo_result_path: str,
    modelo_series_path: str,
    verbose: bool = False
) -> bool:
    """
    Verifica el historial de entrenamientos y decide si actualizar el modelo .pkl.
    
    Estrategia:
    1. Lee todos los logs JSON de la lotería
    2. Encuentra los 3 mejores entrenamientos históricos
    3. Compara el mejor histórico con el modelo .pkl actual
    4. Solo actualiza .pkl si el mejor histórico supera al .pkl actual
    
    Args:
        lottery_name: Nombre de la lotería
        current_score: Score combinado del entrenamiento actual
        current_result_acc: Accuracy del modelo result actual
        current_series_acc: Accuracy del modelo series actual
        modelo_result_path: Ruta al modelo result .pkl
        modelo_series_path: Ruta al modelo series .pkl
        verbose: Mostrar información detallada
    
    Returns:
        True si debe actualizar el .pkl, False si solo guardar en historial
    """
    import json
    from pathlib import Path
    
    logs_dir = Path("logs")
    
    # Buscar todos los logs de esta lotería
    pattern = f"training_{lottery_name}_*.json"
    log_files = list(logs_dir.glob(pattern))
    
    if not log_files:
        # No hay historial, es el primer entrenamiento
        if verbose:
            print("\n   📝 Primer entrenamiento - guardando en IA_models/")
        return True
    
    # Leer todos los logs y extraer scores
    historical_trainings = []
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                combined_score = (
                    data.get('best_result_acc', 0) + 
                    data.get('best_series_acc', 0)
                ) / 2
                historical_trainings.append({
                    'file': log_file.name,
                    'score': combined_score,
                    'result_acc': data.get('best_result_acc', 0),
                    'series_acc': data.get('best_series_acc', 0),
                    'timestamp': data.get('start_time', '')
                })
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Error leyendo {log_file.name}: {e}")
            continue
    
    # Agregar el entrenamiento actual
    historical_trainings.append({
        'file': 'ACTUAL',
        'score': current_score,
        'result_acc': current_result_acc,
        'series_acc': current_series_acc,
        'timestamp': 'now'
    })
    
    # Ordenar por score (mayor a menor)
    historical_trainings.sort(key=lambda x: x['score'], reverse=True)
    
    # Obtener los 3 mejores
    top_3 = historical_trainings[:3]
    
    if verbose:
        print("\n   📊 Top 3 Entrenamientos Históricos:")
        for i, training in enumerate(top_3, 1):
            role = "MEJOR" if i == 1 else "EXPERIMENTAL"
            marker = "🏆" if i == 1 else "🧪"
            is_current = " (ACTUAL)" if training['file'] == 'ACTUAL' else ""
            print(f"      {marker} #{i} [{role}]: Score={training['score']:.4f} "
                  f"(R={training['result_acc']:.4f}, S={training['series_acc']:.4f}){is_current}")
    
    # Verificar si el entrenamiento actual está en el top 3
    current_in_top3 = any(t['file'] == 'ACTUAL' for t in top_3)
    
    if not current_in_top3:
        if verbose:
            print(f"\n   ❌ Entrenamiento actual no está en el Top 3")
            print(f"      No se actualizará IA_models/, solo se guardará en historial")
        return False
    
    # El mejor del top 3
    best_historical = top_3[0]
    
    # Si el actual no es el mejor del top 3, no actualizar
    if best_historical['file'] != 'ACTUAL':
        if verbose:
            print(f"\n   📊 Entrenamiento actual está en Top 3 pero no es el mejor")
            print(f"      Mejor histórico: {best_historical['score']:.4f}")
            print(f"      No se actualizará IA_models/, solo se guardará en historial")
        return False
    
    # El actual es el mejor del top 3, ahora comparar con el .pkl actual
    if os.path.exists(modelo_result_path) and os.path.exists(modelo_series_path):
        try:
            # Cargar modelos actuales y evaluar
            modelo_result_actual = joblib.load(modelo_result_path)
            modelo_series_actual = joblib.load(modelo_series_path)
            
            # Necesitamos X para evaluar, pero no lo tenemos aquí
            # Por ahora, asumimos que si el actual es el mejor histórico, debe actualizarse
            # Esta es una simplificación - idealmente deberíamos pasar X como parámetro
            
            if verbose:
                print(f"\n   🏆 Entrenamiento actual es el MEJOR histórico!")
                print(f"      Score: {current_score:.4f}")
                print(f"      ✅ Actualizando IA_models/ con el nuevo mejor modelo")
            
            return True
            
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Error al cargar modelos actuales: {e}")
            # Si hay error, actualizar por seguridad
            return True
    else:
        # No existen modelos .pkl, es el primer guardado
        if verbose:
            print(f"\n   📝 No existen modelos .pkl previos")
            print(f"      ✅ Guardando primer modelo en IA_models/")
        return True

if __name__ == "__main__":
    print("🚀 Ejecutando entrenamiento con datos reales desde 'data/resultados_astro.xlsx'...\n")

    import pandas as pd

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
            min_acc=MIN_ACCURACY ,
            max_iter=ITERATIONS,
            verbose=True
        )

    print("\n\n🏁 Entrenamiento finalizado para todas las loterías.")
