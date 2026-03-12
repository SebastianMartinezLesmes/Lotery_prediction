import random
import warnings
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score
from src.core.config import settings
from joblib import Parallel, delayed
from collections import Counter


# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning)


# =========================
# Crear población inicial
# =========================

def probabilidad_mutacion(generacion, max_generaciones):

    base = settings.MUTATION_PROBABILITY

    factor = 1 - (generacion / max_generaciones)

    return base + (0.3 * factor)


# =========================
# Crear población inicial
# =========================

def crear_poblacion_inicial(size):
    poblacion = []
    for _ in range(size):
        params = {
            "n_estimators": random.randint(*settings.RF_N_ESTIMATORS_RANGE),
            "max_depth": random.choice(settings.RF_MAX_DEPTH_OPTIONS),
            "min_samples_split": random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE),
            "min_samples_leaf": random.randint(1,5),
            "max_features": random.choice(["sqrt","log2",None]),
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
        hijo[key] = random.choice([padre1[key], padre2[key]])

    return hijo


# =========================
# Mutación genética
# =========================

def mutar_parametros(params, generacion, max_generaciones):

    nuevo = params.copy()

    prob = probabilidad_mutacion(generacion, max_generaciones)

    if random.random() < prob:
        nuevo["n_estimators"] += random.randint(
            -settings.MUTATION_ESTIMATOR_STEP,
            settings.MUTATION_ESTIMATOR_STEP
        )

    if random.random() < prob:
        nuevo["max_depth"] = random.choice(settings.RF_MAX_DEPTH_OPTIONS)

    if random.random() < prob:
        nuevo["min_samples_split"] = random.randint(
            *settings.RF_MIN_SAMPLES_SPLIT_RANGE
        )

    if random.random() < prob:
        nuevo["min_samples_leaf"] = random.randint(1,5)

    if random.random() < prob:
        nuevo["max_features"] = random.choice(["sqrt","log2",None])

    nuevo["n_estimators"] = max(10, nuevo["n_estimators"])
    return nuevo


# =========================
# Evaluar individuo
# =========================

def evaluar_individuo(params, X_train, y_train, X_test, y_test):

    model = RandomForestClassifier(**params)
    conteo = Counter(y_train)
    min_class = min(conteo.values())
    cv = min(3, min_class)

    if cv < 2:
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        acc = accuracy_score(y_test, pred)
        return acc, model

    scores = cross_val_score(
        model,
        X_train,
        y_train,
        cv=cv,
        n_jobs=1
    )

    acc = scores.mean()
    model.fit(X_train, y_train)
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

def crear_nueva_generacion(elite, poblacion_size, generacion, max_generaciones):

    nueva = [e["params"] for e in elite]

    while len(nueva) < poblacion_size:

        padre1 = random.choice(elite)["params"]
        padre2 = random.choice(elite)["params"]

        hijo = crossover(padre1, padre2)

        hijo = mutar_parametros(
            hijo,
            generacion,
            max_generaciones
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

        print(f"Baseline accuracy: {mejor_acc:.4f}")

    for g in range(generaciones):

        # Evaluación paralela

        resultados_eval = Parallel(n_jobs=-1)(
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
                mejor_acc = acc
                mejor_modelo = model
        
        gen_best = max(resultados, key=lambda x: x["accuracy"])
        gen_best_acc = gen_best["accuracy"]
        gen_best_params = gen_best["params"]

        elite = seleccionar_mejores(
            resultados,
            top_k=settings.EVOLUTION_ELITE_SIZE
        )

        poblacion = crear_nueva_generacion(
            elite,
            poblacion_size,
            g,
            generaciones
        )

        # ---------------------
        # Log
        # ---------------------

        print(
            f"Gen {g+1}/{generaciones} | Best accuracy {tipo_modelo}: {gen_best_acc:.4f}"
        )
        
    if mejor_modelo is None:

        mejor_modelo = RandomForestClassifier()
        mejor_modelo.fit(X_train, y_train)

        pred = mejor_modelo.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
    
    return mejor_modelo, mejor_acc