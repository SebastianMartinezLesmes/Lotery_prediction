"""
Entrenamiento por dígitos con algoritmo genético real.

Modos:
  test  → 2 iteraciones de random search, secuencial, verificación rápida.
  prod  → algoritmo genético: población → selección → cruce → mutación,
          en paralelo por generación, con early stopping.

Diferencia clave respecto a random search:
  - Random search: cada candidato es completamente aleatorio, independiente.
  - Genético real: cada generación HEREDA y REFINA los mejores parámetros
    de la generación anterior. Los nuevos candidatos se generan cruzando
    y mutando a los mejores, no tomando valores al azar del espacio completo.

Ciclo genético por generación:
  1. Evaluar todos los individuos de la población (en paralelo)
  2. Ordenar por fitness (accuracy)
  3. Conservar los `elite` mejores sin cambios
  4. Generar el resto cruzando pares del top-50% + mutación
  5. Si el mejor de la generación no supera al mejor global → sumar patience
  6. Early stop si patience se agota
"""
import os
import warnings
import numpy as np
import joblib as jl

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from src.utils.save_training import guardar_modelo_si_mejora, crear_base_modelos_IA

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# Modelo compuesto: 4 RF (uno por dígito)
# ─────────────────────────────────────────────────────────────────────────────

class _ModeloCompuesto:
    """
    Encapsula 4 RF de dígitos.
      predict()       → reconstruye el número completo
      top3_numeros()  → top 3 combinaciones con probabilidad conjunta
    """

    def __init__(self, miles, centenas, decenas, unidades, n_features_in_):
        self.miles          = miles
        self.centenas       = centenas
        self.decenas        = decenas
        self.unidades       = unidades
        self.n_features_in_ = n_features_in_

    def predict(self, X):
        return (
            self.miles.predict(X)      * 1000
            + self.centenas.predict(X) * 100
            + self.decenas.predict(X)  * 10
            + self.unidades.predict(X)
        )

    def top3_numeros(self, X):
        def top_k(model, k=2):
            p   = model.predict_proba(X)[0]
            idx = np.argsort(p)[-k:][::-1]
            return [(int(model.classes_[i]), float(p[i])) for i in idx]

        candidatos = [
            (m * 1000 + c * 100 + d * 10 + u, pm * pc * pd * pu)
            for m, pm in top_k(self.miles)
            for c, pc in top_k(self.centenas)
            for d, pd in top_k(self.decenas)
            for u, pu in top_k(self.unidades)
        ]
        candidatos.sort(key=lambda x: x[1], reverse=True)
        return candidatos[:3]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de entrenamiento
# ─────────────────────────────────────────────────────────────────────────────

def _entrenar_rf(X_tr, y_tr, X_te, y_te,
                 n_estimators, max_depth, seed, min_samples_split):
    """Entrena un RF y retorna (modelo, accuracy)."""
    m = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        class_weight="balanced",
        random_state=seed,
        n_jobs=1,
    )
    m.fit(X_tr, y_tr)
    return m, accuracy_score(y_te, m.predict(X_te))


def _evaluar_individuo(individuo, test_size,
                       X, y_miles, y_centenas, y_decenas, y_unidades, y_series):
    """
    Evalúa un individuo (dict de hiperparámetros) entrenando los 5 modelos.
    Pensado para ejecutarse en paralelo con joblib.

    Split cronológico de 3 bloques fijos (70 / 15 / 15):
      - train : primeras 70 %  filas
      - val   : siguientes 15 % filas  → fitness del algoritmo genético
      - test  : últimas 15 %  filas   → métricas de evaluación (no usadas en fitness)

    Retorna el individuo enriquecido con modelos, fitness (sobre val) y
    acc_test_result / acc_test_series (sobre test, informativos).
    """
    seed  = individuo["seed"]
    n_est = individuo["n_estimators"]
    depth = individuo["max_depth"]
    split = individuo["min_samples_split"]

    n = len(X)
    n_test  = int(n * 0.15)
    n_val   = int(n * 0.15)
    n_train = n - n_val - n_test

    X_tr  = X[:n_train]
    X_val = X[n_train:n_train + n_val]
    X_te  = X[n_train + n_val:]

    ym_tr,  ym_val,  ym_te  = y_miles[:n_train],    y_miles[n_train:n_train+n_val],    y_miles[n_train+n_val:]
    yc_tr,  yc_val,  yc_te  = y_centenas[:n_train],  y_centenas[n_train:n_train+n_val],  y_centenas[n_train+n_val:]
    yd_tr,  yd_val,  yd_te  = y_decenas[:n_train],   y_decenas[n_train:n_train+n_val],   y_decenas[n_train+n_val:]
    yu_tr,  yu_val,  yu_te  = y_unidades[:n_train],  y_unidades[n_train:n_train+n_val],  y_unidades[n_train+n_val:]
    ys_tr,  ys_val,  ys_te  = y_series[:n_train],    y_series[n_train:n_train+n_val],    y_series[n_train+n_val:]

    # Entrenar sobre train, evaluar fitness sobre VAL (el genético optimiza en val)
    m_m, acc_m_val = _entrenar_rf(X_tr, ym_tr, X_val, ym_val, n_est, depth, seed, split)
    m_c, acc_c_val = _entrenar_rf(X_tr, yc_tr, X_val, yc_val, n_est, depth, seed, split)
    m_d, acc_d_val = _entrenar_rf(X_tr, yd_tr, X_val, yd_val, n_est, depth, seed, split)
    m_u, acc_u_val = _entrenar_rf(X_tr, yu_tr, X_val, yu_val, n_est, depth, seed, split)
    m_s, acc_s_val = _entrenar_rf(X_tr, ys_tr, X_val, ys_val, n_est, depth, seed, split)

    acc_result_val = (acc_m_val + acc_c_val + acc_d_val + acc_u_val) / 4

    # Evaluar sobre TEST (solo informativo, no usados en fitness)
    acc_m_te = accuracy_score(ym_te, m_m.predict(X_te))
    acc_c_te = accuracy_score(yc_te, m_c.predict(X_te))
    acc_d_te = accuracy_score(yd_te, m_d.predict(X_te))
    acc_u_te = accuracy_score(yu_te, m_u.predict(X_te))
    acc_s_te = accuracy_score(ys_te, m_s.predict(X_te))
    acc_result_test = (acc_m_te + acc_c_te + acc_d_te + acc_u_te) / 4

    return {
        **individuo,
        "m_m": m_m, "m_c": m_c, "m_d": m_d, "m_u": m_u, "m_s": m_s,
        "fitness_result":   acc_result_val,
        "fitness_series":   acc_s_val,
        "acc_test_result":  acc_result_test,
        "acc_test_series":  acc_s_te,
        # per-digit val accuracies (used in T7 baseline table)
        "acc_m_te": acc_m_te, "acc_c_te": acc_c_te,
        "acc_d_te": acc_d_te, "acc_u_te": acc_u_te,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Operadores genéticos
# ─────────────────────────────────────────────────────────────────────────────

def _individuo_aleatorio(rng, n_est_opts, depth_opts, split_opts):
    """Crea un individuo con genes completamente aleatorios."""
    return {
        "n_estimators":      int(rng.choice(n_est_opts)),
        "max_depth":         rng.choice(depth_opts),
        "min_samples_split": int(rng.choice(split_opts)),
        "seed":              int(rng.integers(0, 10000)),
    }


def _cruzar(padre1, padre2, rng):
    """
    Cruce uniforme: cada gen del hijo se toma de padre1 o padre2 con p=0.5.
    El seed siempre es nuevo (variabilidad en la partición train/test).
    """
    genes = ["n_estimators", "max_depth", "min_samples_split"]
    hijo = {}
    for gen in genes:
        hijo[gen] = padre1[gen] if rng.random() < 0.5 else padre2[gen]
    hijo["seed"] = int(rng.integers(0, 10000))
    return hijo


def _mutar(individuo, rng, prob, n_est_opts, depth_opts, split_opts):
    """
    Mutación gen a gen: cada parámetro muta con probabilidad `prob`.
    La mutación NO toma un valor completamente aleatorio — elige entre
    los vecinos del valor actual en el espacio de búsqueda (mutación local),
    lo que preserva la información del padre mientras introduce variación.
    """
    hijo = dict(individuo)
    hijo["seed"] = int(rng.integers(0, 10000))  # seed siempre nuevo

    if rng.random() < prob:
        # Mutación local: paso ±1 en la lista de opciones
        idx = list(n_est_opts).index(hijo["n_estimators"])
        delta = rng.choice([-1, 0, 1])
        idx_nuevo = max(0, min(len(n_est_opts) - 1, idx + delta))
        hijo["n_estimators"] = int(n_est_opts[idx_nuevo])

    if rng.random() < prob:
        idx = list(depth_opts).index(hijo["max_depth"])
        delta = rng.choice([-1, 0, 1])
        idx_nuevo = max(0, min(len(depth_opts) - 1, idx + delta))
        hijo["max_depth"] = depth_opts[idx_nuevo]

    if rng.random() < prob:
        idx = list(split_opts).index(hijo["min_samples_split"])
        delta = rng.choice([-1, 0, 1])
        idx_nuevo = max(0, min(len(split_opts) - 1, idx + delta))
        hijo["min_samples_split"] = int(split_opts[idx_nuevo])

    return hijo


def _nueva_generacion(poblacion_evaluada, tam_poblacion, elite,
                      prob_mutacion, rng, n_est_opts, depth_opts, split_opts):
    """
    Genera la siguiente generación a partir de la población evaluada.

    1. Ordena por fitness_result (descendente)
    2. Los `elite` mejores pasan directos (elitismo)
    3. El resto se genera cruzando pares aleatorios del top-50% + mutación
    """
    ordenada = sorted(poblacion_evaluada,
                      key=lambda x: x["fitness_result"], reverse=True)
    nueva = []

    # Elitismo: los mejores pasan sin cambio (solo nuevo seed para re-evaluar)
    for ind in ordenada[:elite]:
        clon = {k: v for k, v in ind.items()
                if k in ("n_estimators", "max_depth", "min_samples_split")}
        clon["seed"] = int(rng.integers(0, 10000))
        nueva.append(clon)

    # Mating pool: top 50% de la población
    pool = ordenada[:max(2, len(ordenada) // 2)]

    while len(nueva) < tam_poblacion:
        # Selección por torneo (k=2): más diversidad que seleccionar siempre top-2
        idx_a = int(rng.integers(0, len(pool)))
        idx_b = int(rng.integers(0, len(pool)))
        padre1 = pool[idx_a] if pool[idx_a]["fitness_result"] >= pool[idx_b]["fitness_result"] else pool[idx_b]

        idx_c = int(rng.integers(0, len(pool)))
        idx_d = int(rng.integers(0, len(pool)))
        padre2 = pool[idx_c] if pool[idx_c]["fitness_result"] >= pool[idx_d]["fitness_result"] else pool[idx_d]

        hijo = _cruzar(padre1, padre2, rng)
        hijo = _mutar(hijo, rng, prob_mutacion, n_est_opts, depth_opts, split_opts)
        nueva.append(hijo)

    return nueva[:tam_poblacion]


# ─────────────────────────────────────────────────────────────────────────────
# Entrenamiento principal
# ─────────────────────────────────────────────────────────────────────────────

def entrenar_modelos_por_loteria(
    X, y_result, y_series,
    nombre_loteria,
    min_acc=None,
    max_iter=None,   # ignorado en modo genético, se usa generaciones×poblacion
    verbose=True,
):
    """
    Entrena modelos para una lotería.

    Modo test → random search secuencial, 2 iteraciones.
    Modo prod → algoritmo genético con paralelismo por generación.
    """
    from src.core.config import settings
    from multiprocessing import cpu_count

    profile      = settings.get_training_profile()
    min_acc      = min_acc if min_acc is not None else profile["min_accuracy"]
    test_size    = profile["test_size"]
    n_jobs       = profile.get("n_jobs", 1)
    if n_jobs == -1:
        n_jobs = cpu_count()

    n_est_opts   = profile["n_estimators"]
    depth_opts   = profile["max_depth"]
    split_opts   = profile["min_samples_split"]
    mode_label   = os.getenv("TRAINING_MODE", "prod").upper()

    # ── Dígitos del resultado ─────────────────────────────────────────────
    y_miles    = (y_result // 1000) % 10
    y_centenas = (y_result // 100)  % 10
    y_decenas  = (y_result // 10)   % 10
    y_unidades =  y_result          % 10

    # ── Cargar baseline de modelos previos ────────────────────────────────
    mejor_acc_result    = -1.0
    mejor_acc_series    = -1.0
    mejor_modelo_result = None
    mejor_modelo_series = None

    base = crear_base_modelos_IA(nombre_loteria)
    for path in base["result"]:
        if os.path.exists(path):
            try:
                payload = jl.load(path)
                acc = payload.get("accuracy", 0)
                if acc > mejor_acc_result:
                    mejor_acc_result    = acc
                    mejor_modelo_result = payload["model"]
                    if verbose:
                        print(f"[ok] Result previo  (baseline: {acc:.4f})")
            except Exception:
                pass

    for path in base["series"]:
        if os.path.exists(path):
            try:
                payload = jl.load(path)
                acc = payload.get("accuracy", 0)
                if acc > mejor_acc_series:
                    mejor_acc_series    = acc
                    mejor_modelo_series = payload["model"]
                    if verbose:
                        print(f"[ok] Series previo  (baseline: {acc:.4f})")
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────
    # MODO TEST — random search secuencial (igual que antes)
    # ─────────────────────────────────────────────────────────────────────
    if n_jobs == 1:
        max_iter_test = profile.get("max_iter", 2)
        rng = np.random.default_rng()

        if verbose:
            print(f"\n{'='*60}")
            print(f"Modo: {mode_label}  |  Entrenando: {nombre_loteria.upper()}")
            print(f"Registros : {len(X)}  |  Features: {X.shape[1]}")
            print(f"Iteraciones: {max_iter_test}  |  n_jobs: 1 (secuencial)")
            print("=" * 60)

        # Track best individual (unused for now; per-digit test computed in final block)
        mejor_res_individuo    = None
        mejor_series_individuo = None

        for intento in range(1, max_iter_test + 1):
            ind = _individuo_aleatorio(rng, n_est_opts, depth_opts, split_opts)
            res = _evaluar_individuo(ind, test_size,
                                     X, y_miles, y_centenas, y_decenas,
                                     y_unidades, y_series)
            marcas = ""
            if res["fitness_result"] > mejor_acc_result:
                mejor_acc_result    = res["fitness_result"]
                mejor_modelo_result = _ModeloCompuesto(
                    res["m_m"], res["m_c"], res["m_d"], res["m_u"], X.shape[1])
                mejor_res_individuo = res
                marcas += " *result"
            if res["fitness_series"] > mejor_acc_series:
                mejor_acc_series    = res["fitness_series"]
                mejor_modelo_series = res["m_s"]
                mejor_series_individuo = res
                marcas += " *series"
            if verbose:
                print(f"  [{intento}/{max_iter_test}] "
                      f"n_est={res['n_estimators']} "
                      f"depth={str(res['max_depth']):<4} | "
                      f"acc_val={res['fitness_result']:.4f} "
                      f"acc_test={res['acc_test_result']:.4f} "
                      f"series_val={res['fitness_series']:.4f} "
                      f"series_test={res['acc_test_series']:.4f}{marcas}")

    # ─────────────────────────────────────────────────────────────────────
    # MODO PROD — algoritmo genético con paralelismo
    # ─────────────────────────────────────────────────────────────────────
    else:
        generaciones  = profile.get("generaciones", 15)
        tam_poblacion = profile.get("poblacion", 8)
        elite         = profile.get("elite", 2)
        prob_mutacion = profile.get("prob_mutacion", 0.3)
        patience      = profile.get("patience", 5)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Modo: {mode_label}  |  Entrenando: {nombre_loteria.upper()}")
            print(f"Registros : {len(X)}  |  Features: {X.shape[1]}")
            print(f"Generaciones: {generaciones}  |  Población: {tam_poblacion}  "
                  f"|  Elite: {elite}  |  n_jobs: {n_jobs}")
            print(f"Mutación: {prob_mutacion}  |  Patience: {patience} gen sin mejora")
            print(f"n_estimators: {n_est_opts}")
            print(f"max_depth   : {depth_opts}")
            print("=" * 60)

        rng        = np.random.default_rng()
        sin_mejora = 0

        # Track best individual to extract per-digit test accuracies for T7
        mejor_res_individuo    = None
        mejor_series_individuo = None

        # Generación 0: población completamente aleatoria
        poblacion = [
            _individuo_aleatorio(rng, n_est_opts, depth_opts, split_opts)
            for _ in range(tam_poblacion)
        ]

        for gen in range(1, generaciones + 1):

            # ── Evaluar población en paralelo ─────────────────────────────
            evaluada = jl.Parallel(n_jobs=n_jobs, prefer="threads")(
                jl.delayed(_evaluar_individuo)(
                    ind, test_size,
                    X, y_miles, y_centenas, y_decenas, y_unidades, y_series,
                )
                for ind in poblacion
            )

            # ── Actualizar mejores globales ───────────────────────────────
            mejor_gen_result = -1.0
            mejor_gen_series = -1.0
            hubo_mejora      = False

            for res in evaluada:
                if res["fitness_result"] > mejor_acc_result:
                    mejor_acc_result    = res["fitness_result"]
                    mejor_modelo_result = _ModeloCompuesto(
                        res["m_m"], res["m_c"], res["m_d"], res["m_u"], X.shape[1])
                    mejor_res_individuo = res
                    hubo_mejora = True
                if res["fitness_series"] > mejor_acc_series:
                    mejor_acc_series    = res["fitness_series"]
                    mejor_modelo_series = res["m_s"]
                    mejor_series_individuo = res
                    hubo_mejora = True
                mejor_gen_result = max(mejor_gen_result, res["fitness_result"])
                mejor_gen_series = max(mejor_gen_result, res["fitness_series"])

            # ── Mostrar resumen de generación ─────────────────────────────
            if verbose:
                ordenada = sorted(evaluada,
                                  key=lambda x: x["fitness_result"], reverse=True)
                mejor = ordenada[0]
                print(f"\n  Gen {gen}/{generaciones} "
                      f"| mejor_result={mejor_gen_result:.4f} "
                      f"| mejor_series={mejor_gen_series:.4f} "
                      f"{'*' if hubo_mejora else ''}")
                for i, ind in enumerate(ordenada):
                    marcas = ""
                    if ind["fitness_result"] == mejor_acc_result:
                        marcas += " <-best_result"
                    if ind["fitness_series"] == mejor_acc_series:
                        marcas += " <-best_series"
                    print(f"    [{i+1}] n_est={ind['n_estimators']:<3} "
                          f"depth={str(ind['max_depth']):<4} "
                          f"split={ind['min_samples_split']} | "
                          f"result={ind['fitness_result']:.4f} "
                          f"series={ind['fitness_series']:.4f}{marcas}")

            # ── Early stopping ────────────────────────────────────────────
            if not hubo_mejora:
                sin_mejora += 1
            else:
                sin_mejora = 0

            if sin_mejora >= patience:
                if verbose:
                    print(f"\n  [stop] Early stop: {sin_mejora} generaciones sin mejora global.")
                break

            # ── Evolucionar: generar siguiente generación ─────────────────
            if gen < generaciones:
                poblacion = _nueva_generacion(
                    evaluada, tam_poblacion, elite,
                    prob_mutacion, rng, n_est_opts, depth_opts, split_opts,
                )
                if verbose:
                    print(f"  -> Generacion {gen+1}: "
                          f"{elite} élite + {tam_poblacion-elite} hijos")

    # ── Resultado final (T6) ─────────────────────────────────────────────
    # Calcular accuracy de test del mejor modelo sobre bloque test (70/15/15)
    from collections import Counter

    n = len(X)
    n_test  = int(n * 0.15)
    n_val   = int(n * 0.15)
    n_train = n - n_val - n_test

    X_te_final = X[n_train + n_val:]
    ym_te_final = y_miles[n_train + n_val:]
    yc_te_final = y_centenas[n_train + n_val:]
    yd_te_final = y_decenas[n_train + n_val:]
    yu_te_final = y_unidades[n_train + n_val:]
    ys_te_final = y_series[n_train + n_val:]

    # Per-digit test accuracies for the best result model
    if mejor_modelo_result is not None:
        acc_miles_test    = accuracy_score(ym_te_final, mejor_modelo_result.miles.predict(X_te_final))
        acc_cent_test     = accuracy_score(yc_te_final, mejor_modelo_result.centenas.predict(X_te_final))
        acc_dec_test      = accuracy_score(yd_te_final, mejor_modelo_result.decenas.predict(X_te_final))
        acc_uni_test      = accuracy_score(yu_te_final, mejor_modelo_result.unidades.predict(X_te_final))
        accuracy_test_result = (acc_miles_test + acc_cent_test + acc_dec_test + acc_uni_test) / 4
    else:
        acc_miles_test = acc_cent_test = acc_dec_test = acc_uni_test = 0.0
        accuracy_test_result = 0.0

    if mejor_modelo_series is not None:
        acc_series_test      = accuracy_score(ys_te_final, mejor_modelo_series.predict(X_te_final))
        accuracy_test_series = acc_series_test
    else:
        acc_series_test      = 0.0
        accuracy_test_series = 0.0

    # accuracy_val comes from the fitness (optimized over validation block)
    accuracy_val_result = mejor_acc_result
    accuracy_val_series = mejor_acc_series

    if verbose:
        print(f"\n  Mejor result acc_val : {accuracy_val_result:.4f}  |  acc_test: {accuracy_test_result:.4f}")
        print(f"  Mejor series acc_val : {accuracy_val_series:.4f}  |  acc_test: {accuracy_test_series:.4f}")

    # ── Líneas base sobre bloque TEST (T7) ───────────────────────────────
    y_miles_te    = (y_result[n_train + n_val:] // 1000) % 10
    y_centenas_te = (y_result[n_train + n_val:] // 100)  % 10
    y_decenas_te  = (y_result[n_train + n_val:] // 10)   % 10
    y_unidades_te =  y_result[n_train + n_val:] % 10
    y_series_te   =  y_series[n_train + n_val:]

    base_miles    = max(Counter(y_miles_te).values())    / len(y_miles_te)
    base_centenas = max(Counter(y_centenas_te).values()) / len(y_centenas_te)
    base_decenas  = max(Counter(y_decenas_te).values())  / len(y_decenas_te)
    base_unidades = max(Counter(y_unidades_te).values()) / len(y_unidades_te)
    base_series   = max(Counter(y_series_te).values())   / len(y_series_te)

    if verbose:
        print(f"\n=== LÍNEAS BASE (bloque test) ===")
        print(f"  {'Target':<12} {'Modelo':>10} {'Azar':>10} {'Más_frecuente':>15}")
        print(f"  {'Miles':<12} {acc_miles_test:>10.2%} {'10.00%':>10} {base_miles:>15.2%}")
        print(f"  {'Centenas':<12} {acc_cent_test:>10.2%} {'10.00%':>10} {base_centenas:>15.2%}")
        print(f"  {'Decenas':<12} {acc_dec_test:>10.2%} {'10.00%':>10} {base_decenas:>15.2%}")
        print(f"  {'Unidades':<12} {acc_uni_test:>10.2%} {'10.00%':>10} {base_unidades:>15.2%}")
        print(f"  {'Signo':<12} {acc_series_test:>10.2%} {'8.33%':>10} {base_series:>15.2%}")

    # ── Guardar en memoria IA ─────────────────────────────────────────────
    print("\n🧠 Guardando en memoria IA:")
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="result",
        modelo=mejor_modelo_result,
        accuracy=accuracy_val_result,
        n_records=len(X),
        accuracy_val=accuracy_val_result,
        accuracy_test=accuracy_test_result,
    )
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="series",
        modelo=mejor_modelo_series,
        accuracy=accuracy_val_series,
        n_records=len(X),
        accuracy_val=accuracy_val_series,
        accuracy_test=accuracy_test_series,
    )

    if verbose:
        print(f"\n[OK] Entrenamiento completado")
        print(f"   Mejor result acc_val: {accuracy_val_result:.4f}  acc_test: {accuracy_test_result:.4f}")
        print(f"   Mejor series acc_val: {accuracy_val_series:.4f}  acc_test: {accuracy_test_series:.4f}")

    return mejor_modelo_result, mejor_modelo_series
