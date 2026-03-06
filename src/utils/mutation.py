import random
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


# =========================
# Crear población inicial
# =========================

def crear_poblacion_inicial(size):

    poblacion = []

    for _ in range(size):

        params = {
            "n_estimators": random.randint(50, 400),
            "max_depth": random.choice([3,4,5,6,8,10,None]),
            "min_samples_split": random.randint(2,10)
        }

        poblacion.append(params)

    return poblacion


# =========================
# Mutación genética
# =========================

def mutar_parametros(params):

    nuevo = params.copy()

    if random.random() < 0.4:
        nuevo["n_estimators"] += random.randint(-50,50)

    if random.random() < 0.4:
        nuevo["max_depth"] = random.choice([3,4,5,6,8,10,None])

    if random.random() < 0.4:
        nuevo["min_samples_split"] = random.randint(2,10)

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

def seleccionar_mejores(resultados, top_k=5):

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
    generaciones=50,
    poblacion_size=20
):

    poblacion = crear_poblacion_inicial(poblacion_size)

    mejor_modelo = None
    mejor_acc = 0

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

        elite = seleccionar_mejores(resultados, top_k=5)

        poblacion = crear_nueva_generacion(
            elite,
            poblacion_size
        )

        print(
            f"Gen {g} | Best accuracy: {mejor_acc:.4f}"
        )

    if mejor_modelo is None:
        # fallback seguro
        mejor_modelo = RandomForestClassifier()
        mejor_modelo.fit(X_train, y_train)

        pred = mejor_modelo.predict(X_test)
        mejor_acc = accuracy_score(y_test, pred)
        
    return mejor_modelo, mejor_acc