import random
import warnings
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score
from src.core.config import settings
from joblib import Parallel, delayed
from collections import Counter

# Importar modelos opcionales
try:
    from xgboost import XGBClassifier
    XGBOOST_DISPONIBLE = True
except ImportError:
    XGBOOST_DISPONIBLE = False

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_DISPONIBLE = True
except ImportError:
    LIGHTGBM_DISPONIBLE = False

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# =========================
# Probabilidad de mutación
# =========================

def probabilidad_mutacion(generacion, max_generaciones):

    base = settings.MUTATION_PROBABILITY

    factor = 1 - (generacion / max_generaciones)

    return base + (0.3 * factor)


# =========================
# Crear población inicial
# =========================

def crear_poblacion_inicial(size):
    """Crea población mixta: RF + XGBoost + LightGBM si están disponibles."""
    tipos_disponibles = ["rf"]
    if XGBOOST_DISPONIBLE:
        tipos_disponibles.append("xgb")
    if LIGHTGBM_DISPONIBLE:
        tipos_disponibles.append("lgbm")

    poblacion = []
    for _ in range(size):
        tipo = random.choice(tipos_disponibles)
        if tipo == "xgb":
            params = {
                "tipo_modelo": "xgb",
                "n_estimators": random.randint(50, 300),
                "max_depth": random.choice([3, 4, 5, 6, 8]),
                "learning_rate": random.choice([0.01, 0.05, 0.1, 0.2]),
                "subsample": random.choice([0.6, 0.7, 0.8, 0.9, 1.0]),
                "random_state": random.randint(0, 10000)
            }
        elif tipo == "lgbm":
            params = {
                "tipo_modelo": "lgbm",
                "n_estimators": random.randint(50, 300),
                "max_depth": random.choice([3, 4, 5, 6, 8]),
                "learning_rate": random.choice([0.01, 0.05, 0.1, 0.2]),
                "num_leaves": random.choice([15, 31, 63, 127]),
                "random_state": random.randint(0, 10000)
            }
        else:
            params = {
                "tipo_modelo": "rf",
                "n_estimators": random.randint(*settings.RF_N_ESTIMATORS_RANGE),
                "max_depth": random.choice(settings.RF_MAX_DEPTH_OPTIONS),
                "min_samples_split": random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE),
                "min_samples_leaf": random.randint(1, 5),
                "max_features": random.choice(["sqrt", "log2", None]),
                "random_state": random.randint(*settings.MODEL_RANDOM_STATE_RANGE)
            }
        poblacion.append(params)
    return poblacion


# =========================
# Cruce genetico
# =========================

def crossover(padre1, padre2):
    hijo = {}

    for key in padre1.keys():

        if isinstance(padre1[key], int) and isinstance(padre2[key], int):
            hijo[key] = random.choice([
                padre1[key],
                padre2[key],
                (padre1[key] + padre2[key]) // 2
            ])
        else:
            hijo[key] = random.choice([padre1[key], padre2[key]])

    return hijo


# Direccion de mejora

def mutar_hacia_mejor(params, mejor_params, fuerza=0.3):
    nuevo = params.copy()
    for k in ["n_estimators", "min_samples_split", "min_samples_leaf"]:
        if k in params and k in mejor_params:
            if isinstance(params[k], int) and isinstance(mejor_params[k], int):
                direccion = mejor_params[k] - params[k]
                nuevo[k] = int(params[k] + direccion * fuerza)
    return nuevo


# Mutacion distante

def mutacion_lejana(params):

    nuevo = params.copy()

    nuevo["n_estimators"] = random.randint(*settings.RF_N_ESTIMATORS_RANGE)
    nuevo["max_depth"] = random.choice(settings.RF_MAX_DEPTH_OPTIONS)
    nuevo["min_samples_split"] = random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE)

    return nuevo


# =========================
# Mutación adaptativa
# =========================

def mutar_parametros(params, generacion, max_generaciones, mejor_params=None, stagnation=False):
    nuevo = params.copy()
    prob = probabilidad_mutacion(generacion, max_generaciones)
    exploration_factor = 1 - (generacion / max_generaciones)

    if stagnation:
        return mutacion_lejana(nuevo)

    tipo = nuevo.get("tipo_modelo", "rf")

    if mejor_params and random.random() < prob:
        fuerza = 0.3 + 0.4 * exploration_factor
        nuevo = mutar_hacia_mejor(nuevo, mejor_params, fuerza=fuerza)

    # Mutaciones comunes
    if random.random() < prob:
        delta = int(nuevo.get("n_estimators", 100) * (0.5 * exploration_factor))
        nuevo["n_estimators"] = max(10, nuevo.get("n_estimators", 100) + random.randint(-delta, delta))

    if random.random() < prob:
        nuevo["max_depth"] = random.choice(settings.RF_MAX_DEPTH_OPTIONS)

    # Mutaciones específicas por tipo
    if tipo == "rf":
        if random.random() < prob:
            nuevo["min_samples_split"] = random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE)
        if random.random() < prob:
            nuevo["min_samples_leaf"] = random.randint(1, 5)
        if random.random() < prob:
            nuevo["max_features"] = random.choice(["sqrt", "log2", None])
    elif tipo in ("xgb", "lgbm"):
        if random.random() < prob:
            nuevo["learning_rate"] = random.choice([0.01, 0.05, 0.1, 0.2])
        if tipo == "lgbm" and random.random() < prob:
            nuevo["num_leaves"] = random.choice([15, 31, 63, 127])

    nuevo["n_estimators"] = max(10, nuevo.get("n_estimators", 100))
    return nuevo


# =========================
# Evaluar individuo
# =========================

def _construir_modelo(params):
    """Construye el modelo según el tipo especificado en params."""
    tipo = params.get("tipo_modelo", "rf")

    if tipo == "xgb" and XGBOOST_DISPONIBLE:
        return XGBClassifier(
            n_estimators=params.get("n_estimators", 100),
            max_depth=params.get("max_depth", 4) or 4,
            learning_rate=params.get("learning_rate", 0.1),
            subsample=params.get("subsample", 0.8),
            random_state=params.get("random_state", 42),
            eval_metric="mlogloss",
            verbosity=0,
            use_label_encoder=False
        )
    elif tipo == "lgbm" and LIGHTGBM_DISPONIBLE:
        return LGBMClassifier(
            n_estimators=params.get("n_estimators", 100),
            max_depth=params.get("max_depth", 4) or 4,
            learning_rate=params.get("learning_rate", 0.1),
            num_leaves=params.get("num_leaves", 31),
            random_state=params.get("random_state", 42),
            verbose=-1
        )
    else:
        # RandomForest por defecto
        return RandomForestClassifier(
            n_estimators=params.get("n_estimators", 200),
            max_depth=params.get("max_depth", 4),
            min_samples_split=params.get("min_samples_split", 5),
            min_samples_leaf=params.get("min_samples_leaf", 1),
            max_features=params.get("max_features", "sqrt"),
            random_state=params.get("random_state", 42)
        )


def evaluar_individuo(params, X_train, y_train, X_test, y_test):
    try:
        model = _construir_modelo(params)
        # Entrenamiento directo sin cross_val (evita MemoryError)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        return acc, model
    except Exception:
        model = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        return acc, model


# =========================
# Selección natural
# =========================

def seleccionar_mejores(resultados, top_k=settings.EVOLUTION_ELITE_SIZE):
    resultados.sort(
        key=lambda x: x["accuracy"],
        reverse=True
    )
    return resultados[:top_k]


# =========================
# Nueva generación
# =========================

def crear_nueva_generacion(elite, poblacion_size, generacion, max_generaciones, mejor_params=None, stagnation=False):
    nueva = [e["params"] for e in elite]

    while len(nueva) < poblacion_size:
        padre1 = random.choice(elite)["params"]
        padre2 = random.choice(elite)["params"]

        hijo = crossover(padre1, padre2)
        hijo = mutar_parametros(
            hijo,
            generacion,
            max_generaciones,
            mejor_params=mejor_params,
            stagnation=stagnation
        )
        nueva.append(hijo)
    return nueva


# =========================
# ENTRENAMIENTO EVOLUTIVO
# =========================

def entrenamiento_evolutivo(
    X_train, y_train,
    X_test,  y_test,
    generaciones=settings.EVOLUTION_GENERATIONS,
    poblacion_size=settings.EVOLUTION_POPULATION_SIZE,
    modelo_base=None,
    tipo_modelo="R"
):
    mejor_modelo = None
    mejor_acc = 0
    stagnation_counter = 0
    direccion_mejora = None

    if modelo_base is None:
        poblacion = crear_poblacion_inicial(poblacion_size)

    else:
        poblacion = crear_poblacion_inicial(poblacion_size - 1)

        params_base = {
            "n_estimators": modelo_base.n_estimators,
            "max_depth": modelo_base.max_depth,
            "min_samples_split": modelo_base.min_samples_split,
            "min_samples_leaf": getattr(modelo_base, "min_samples_leaf", 1),
            "max_features": getattr(modelo_base, "max_features", "sqrt"),
            "random_state": random.randint(*settings.MODEL_RANDOM_STATE_RANGE)
        }

        poblacion.append(params_base)

        pred = modelo_base.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
        mejor_modelo = modelo_base

        print(f"\n Baseline accuracy: {mejor_acc:.4f} \n")

    for g in range(generaciones):

        # Evaluación secuencial con threads (evita MemoryError por fork)
        resultados_eval = Parallel(n_jobs=settings.N_JOBS, prefer="threads")(
            delayed(evaluar_individuo)( params, X_train, y_train, X_test, y_test )
            for params in poblacion
        )

        resultados = []

        for params, (acc, model) in zip(poblacion, resultados_eval):

            resultados.append({
                "accuracy": acc,
                "model": model,
                "params": params
            })
            
            if acc > mejor_acc:
                direccion_mejora = params
                mejor_acc = acc
                mejor_modelo = model
                stagnation_counter = 0 
            else:
                stagnation_counter += 1
        
        stagnation = stagnation_counter > 6

        gen_best = max(resultados, key=lambda x: x["accuracy"])
        gen_best_acc = gen_best["accuracy"]

        elite = seleccionar_mejores(
            resultados,
            top_k=settings.EVOLUTION_ELITE_SIZE
        )

        poblacion = crear_nueva_generacion(
            elite,
            poblacion_size,
            g,
            generaciones,
            mejor_params=direccion_mejora,
            stagnation=stagnation
        )

        poblacion[0] = elite[0]["params"]

        # Log de las generaciones
        print(
            f"Gen {g+1}/{generaciones} | Best acc {tipo_modelo}: {gen_best_acc:.4f}"
        )
        
    if mejor_modelo is None:

        mejor_modelo = RandomForestClassifier()
        mejor_modelo.fit(X_train, y_train)

        pred = mejor_modelo.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
    
    return mejor_modelo, mejor_acc