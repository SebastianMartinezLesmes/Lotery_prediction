import random
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from src.core.config import settings


# =========================
# Crear población inicial
# =========================

def crear_poblacion_inicial(size):
    poblacion = []
    for _ in range(size):
        params = {
            "n_estimators": random.randint(*settings.RF_N_ESTIMATORS_RANGE),
            "max_depth": random.choice(settings.RF_MAX_DEPTH_OPTIONS),
            "min_samples_split": random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE)
        }
        poblacion.append(params)
    return poblacion


# =========================
# Mutación genética
# =========================

def mutar_parametros(params):
    nuevo = params.copy()
    if random.random() < settings.MUTATION_PROBABILITY:
        nuevo["n_estimators"] += random.randint(
            -settings.MUTATION_ESTIMATOR_STEP,
            settings.MUTATION_ESTIMATOR_STEP
        )
    if random.random() < settings.MUTATION_PROBABILITY:
        nuevo["max_depth"] = random.choice(settings.RF_MAX_DEPTH_OPTIONS)
    if random.random() < settings.MUTATION_PROBABILITY:
        nuevo["min_samples_split"] = random.randint(
            *settings.RF_MIN_SAMPLES_SPLIT_RANGE
        )
    nuevo["n_estimators"] = max(10, nuevo["n_estimators"])
    return nuevo

# =========================
# Evaluar individuo
# =========================

def evaluar_individuo(
    params,
    X_train,
    y_train,
    X_test,
    y_test
):
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
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

def crear_nueva_generacion(elite, poblacion_size):

    nueva = []

    while len(nueva) < poblacion_size:

        padre = random.choice(elite)["params"]

        hijo = mutar_parametros(padre)

        nueva.append(hijo)

    return nueva


# =========================
# ENTRENAMIENTO EVOLUTIVO
# =========================

def entrenamiento_evolutivo(
    X_train,
    y_train,
    X_test,
    y_test,
    generaciones=settings.EVOLUTION_GENERATIONS,
    poblacion_size=settings.EVOLUTION_POPULATION_SIZE,
    modelo_base=None,
    tipo_modelo="R"
):
    poblacion = crear_poblacion_inicial(poblacion_size - 1)

    mejor_modelo = None
    mejor_acc = 0

    if modelo_base is None:
        poblacion = crear_poblacion_inicial(poblacion_size)
    else:
        poblacion = crear_poblacion_inicial(poblacion_size - 1)
        params_base = {
            "n_estimators": modelo_base.n_estimators,
            "max_depth": modelo_base.max_depth,
            "min_samples_split": modelo_base.min_samples_split
        }

        poblacion.append(params_base)
        pred = modelo_base.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
        mejor_modelo = modelo_base

        print(f"Baseline accuracy: {mejor_acc:.4f}")

    for g in range(generaciones):

        resultados = []

        for params in poblacion:

            acc, model = evaluar_individuo(
                params,
                X_train,
                y_train,
                X_test,
                y_test
            )

            resultados.append({
                "accuracy": acc,
                "model": model,
                "params": params
            })

            if acc > mejor_acc:
                mejor_acc = acc
                mejor_modelo = model

        elite = seleccionar_mejores(
            resultados,
            top_k=settings.EVOLUTION_ELITE_SIZE
        )

        poblacion = crear_nueva_generacion(
            elite,
            poblacion_size
        )

        print(
            f"Gen {g} | Best accuracy {tipo_modelo}: {mejor_acc:.4f}"
        )

    if mejor_modelo is None:
        
        # fallback seguro
        mejor_modelo = RandomForestClassifier()
        mejor_modelo.fit(X_train, y_train)

        pred = mejor_modelo.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
        
    return mejor_modelo, mejor_acc