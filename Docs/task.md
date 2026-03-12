# planes a implementar

1. Añadir crossover (cruce genético)

2. Mutación adaptativa:
def probabilidad_mutacion(generacion, max_generaciones):
    base = settings.MUTATION_PROBABILITY
    factor = 1 - (generacion / max_generaciones)
    return base + (0.3 * factor)

4. Ampliar el espacio de hiperparámetros:

params = {
    "n_estimators": random.randint(*settings.RF_N_ESTIMATORS_RANGE),
    "max_depth": random.choice(settings.RF_MAX_DEPTH_OPTIONS),
    "min_samples_split": random.randint(*settings.RF_MIN_SAMPLES_SPLIT_RANGE),
    "min_samples_leaf": random.randint(1,5),
    "max_features": random.choice(["sqrt","log2",None])
}

5. Evaluación con Cross Validation:

from sklearn.model_selection import cross_val_score

def evaluar_individuo(params, X_train, y_train, X_test, y_test):
    model = RandomForestClassifier(**params)
    scores = cross_val_score(model, X_train, y_train, cv=3)
    acc = scores.mean()
    model.fit(X_train, y_train)
    return acc, model

10. Paralelizar evaluación

from joblib import Parallel, delayed

resultados = Parallel(n_jobs=-1)(
    delayed(evaluar_individuo)(params, X_train, y_train, X_test, y_test)
    for params in poblacion
)