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
from sklearn.model_selection import train_test_split
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
    Retorna el individuo enriquecido con modelos y fitness.
    """
    seed  = individuo["seed"]
    n_est = individuo["n_estimators"]
    depth = individuo["max_depth"]
    split = individuo["min_samples_split"]

    X_tr, X_te, \
    ym_tr, ym_te, \
    yc_tr, yc_te, \
    yd_tr, yd_te, \
    yu_tr, yu_te, \
    ys_tr, ys_te = train_test_split(
        X, y_miles, y_centenas, y_decenas, y_unidades, y_series,
        test_size=test_size, random_state=seed,
    )

    m_m, acc_m = _entrenar_rf(X_tr, ym_tr, X_te, ym_te, n_est, depth, seed, split)
    m_c, acc_c = _entrenar_rf(X_tr, yc_tr, X_te, yc_te, n_est, depth, seed, split)
    m_d, acc_d = _entrenar_rf(X_tr, yd_tr, X_te, yd_te, n_est, depth, seed, split)
    m_u, acc_u = _entrenar_rf(X_tr, yu_tr, X_te, yu_te, n_est, depth, seed, split)
    m_s, acc_s = _entrenar_rf(X_tr, ys_tr, X_te, ys_te, n_est, depth, seed, split)

    acc_result = (acc_m + acc_c + acc_d + acc_u) / 4

    return {
        **individuo,
        "m_m": m_m, "m_c": m_c, "m_d": m_d, "m_u": m_u, "m_s": m_s,
        "fitness_result": acc_result,
        "fitness_series": acc_s,
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
                        print(f"✓ Result previo  (baseline: {acc:.4f})")
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
                        print(f"✓ Series previo  (baseline: {acc:.4f})")
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
                marcas += " ★result"
            if res["fitness_series"] > mejor_acc_series:
                mejor_acc_series    = res["fitness_series"]
                mejor_modelo_series = res["m_s"]
                marcas += " ★series"
            if verbose:
                print(f"  [{intento}/{max_iter_test}] "
                      f"n_est={res['n_estimators']} "
                      f"depth={str(res['max_depth']):<4} | "
                      f"result={res['fitness_result']:.4f} "
                      f"series={res['fitness_series']:.4f}{marcas}")

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
                    hubo_mejora = True
                if res["fitness_series"] > mejor_acc_series:
                    mejor_acc_series    = res["fitness_series"]
                    mejor_modelo_series = res["m_s"]
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
                      f"{'★' if hubo_mejora else ''}")
                for i, ind in enumerate(ordenada):
                    marcas = ""
                    if ind["fitness_result"] == mejor_acc_result:
                        marcas += " ←best_result"
                    if ind["fitness_series"] == mejor_acc_series:
                        marcas += " ←best_series"
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
                    print(f"\n  ⏹ Early stop: {sin_mejora} generaciones sin mejora global.")
                break

            # ── Evolucionar: generar siguiente generación ─────────────────
            if gen < generaciones:
                poblacion = _nueva_generacion(
                    evaluada, tam_poblacion, elite,
                    prob_mutacion, rng, n_est_opts, depth_opts, split_opts,
                )
                if verbose:
                    print(f"  → Generación {gen+1}: "
                          f"{elite} élite + {tam_poblacion-elite} hijos")

    # ── Resultado final ───────────────────────────────────────────────────
    if verbose:
        print(f"\n  Mejor result acc : {mejor_acc_result:.4f}")
        print(f"  Mejor series acc : {mejor_acc_series:.4f}")

    # ── Guardar en memoria IA ─────────────────────────────────────────────
    print("\n🧠 Guardando en memoria IA:")
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="result",
        modelo=mejor_modelo_result,
        accuracy=mejor_acc_result,
        n_records=len(X),
    )
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="series",
        modelo=mejor_modelo_series,
        accuracy=mejor_acc_series,
        n_records=len(X),
    )

    if verbose:
        print(f"\n✅ Entrenamiento completado")
        print(f"   Mejor result acc: {mejor_acc_result:.4f}")
        print(f"   Mejor series acc: {mejor_acc_series:.4f}")

    return mejor_modelo_result, mejor_modelo_series
