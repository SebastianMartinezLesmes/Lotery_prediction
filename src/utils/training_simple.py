"""
Entrenamiento por dígitos con búsqueda paralela de hiperparámetros.

Modos:
  test  → 2 iteraciones secuenciales, árboles pequeños, verificación rápida.
  prod  → N iteraciones repartidas entre todos los núcleos disponibles,
          con early stopping si el accuracy no mejora en `patience` rondas.

Estrategia:
  - Descompone result en 4 dígitos (miles, centenas, decenas, unidades).
  - Entrena un RF por dígito (10 clases c/u en vez de ~909).
  - En modo prod las iteraciones se lanzan en paralelo con joblib.Parallel,
    reduciendo el tiempo total a ~1/n_jobs respecto al modo secuencial.
  - Early stopping: si en las últimas `patience` iteraciones el mejor
    accuracy no mejora, se detiene sin esperar las restantes.
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
    Encapsula 4 modelos de dígitos.
      predict()       → reconstruye el número completo
      top3_numeros()  → top 3 combinaciones más probables
    """

    def __init__(self, miles, centenas, decenas, unidades, n_features_in_):
        self.miles           = miles
        self.centenas        = centenas
        self.decenas         = decenas
        self.unidades        = unidades
        self.n_features_in_  = n_features_in_

    def predict(self, X):
        return (
            self.miles.predict(X)    * 1000
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
# Helpers internos
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
        n_jobs=1,          # 1 por RF individual; el paralelismo es entre iteraciones
    )
    m.fit(X_tr, y_tr)
    return m, accuracy_score(y_te, m.predict(X_te))


def _una_iteracion(seed, n_est, depth, split, test_size,
                   X, y_miles, y_centenas, y_decenas, y_unidades, y_series):
    """
    Ejecuta una iteración completa de entrenamiento.
    Diseñado para ser llamado en paralelo con joblib.Parallel.

    Returns:
        dict con modelos y accuracies de la iteración.
    """
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
        "m_m": m_m, "m_c": m_c, "m_d": m_d, "m_u": m_u, "m_s": m_s,
        "acc_result": acc_result, "acc_series": acc_s,
        "n_est": n_est, "depth": depth, "split": split,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entrenamiento principal
# ─────────────────────────────────────────────────────────────────────────────

def entrenar_modelos_por_loteria(
    X, y_result, y_series,
    nombre_loteria,
    min_acc=None,
    max_iter=None,
    verbose=True,
):
    """
    Entrena modelos para una lotería.

    En modo test  → secuencial, 2 iteraciones, rápido.
    En modo prod  → paralelo en todos los núcleos disponibles,
                    con early stopping configurable.

    Args:
        X:              Array de features (N, F).
        y_result:       Array de resultados enteros (N,).
        y_series:       Array de series numéricas (N,).
        nombre_loteria: Nombre de la lotería (para guardar modelos).
        min_acc:        Umbral mínimo de accuracy (toma del perfil si None).
        max_iter:       Máximo de iteraciones (toma del perfil si None).
        verbose:        Imprimir progreso.
    """
    from src.core.config import settings
    from multiprocessing import cpu_count

    profile   = settings.get_training_profile()
    min_acc   = min_acc  if min_acc  is not None else profile["min_accuracy"]
    max_iter  = max_iter if max_iter is not None else profile["max_iter"]
    test_size = profile["test_size"]
    patience  = profile.get("patience", max_iter)   # early stop
    n_jobs    = profile.get("n_jobs", 1)
    if n_jobs == -1:
        n_jobs = cpu_count()

    n_est_options = profile["n_estimators"]
    depth_options = profile["max_depth"]
    split_options = profile["min_samples_split"]
    mode_label    = os.getenv("TRAINING_MODE", "prod").upper()

    if verbose:
        print(f"\n{'='*60}")
        print(f"Modo: {mode_label}  |  Entrenando: {nombre_loteria.upper()}")
        print(f"Registros : {len(X)}  |  Features: {X.shape[1]}")
        print(f"Iteraciones: {max_iter}  |  n_jobs: {n_jobs}  |  patience: {patience}")
        print(f"n_estimators: {n_est_options}")
        print(f"max_depth   : {depth_options}")
        print("=" * 60)

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

    # ── Generar todos los hiperparámetros de antemano ─────────────────────
    rng = np.random.default_rng()
    params_list = [
        {
            "seed":  int(rng.integers(0, 10000)),
            "n_est": int(rng.choice(n_est_options)),
            "depth": rng.choice(depth_options),
            "split": int(rng.choice(split_options)),
        }
        for _ in range(max_iter)
    ]

    # ── Ejecutar iteraciones ──────────────────────────────────────────────
    # Modo test  → secuencial (n_jobs=1, sin overhead de Parallel)
    # Modo prod  → paralelo   (n_jobs=CPU disponibles)

    sin_mejora = 0   # contador para early stopping

    if n_jobs == 1:
        # ── Secuencial ───────────────────────────────────────────────────
        for intento, p in enumerate(params_list, 1):
            res = _una_iteracion(
                p["seed"], p["n_est"], p["depth"], p["split"], test_size,
                X, y_miles, y_centenas, y_decenas, y_unidades, y_series,
            )
            mejorado = _actualizar_mejor(res, mejor_acc_result, mejor_acc_series,
                                         mejor_modelo_result, mejor_modelo_series, X)
            mejor_acc_result, mejor_acc_series, \
            mejor_modelo_result, mejor_modelo_series = mejorado

            marcas = ""
            if res["acc_result"] > mejor_acc_result - 1e-6 and \
               res["acc_result"] > (mejor_acc_result if mejor_modelo_result is None else mejor_acc_result - 1e-9):
                marcas += " ★result" if res["acc_result"] > mejor_acc_result else ""
            marcas = (
                (" ★result" if mejorado[0] > mejor_acc_result - 1e-9 and
                               mejorado[0] == res["acc_result"] else "") +
                (" ★series" if mejorado[1] > mejor_acc_series - 1e-9 and
                               mejorado[1] == res["acc_series"] else "")
            )
            # Recalcular marcas de forma simple
            mejor_acc_result, mejor_acc_series, \
            mejor_modelo_result, mejor_modelo_series = mejorado

            if verbose:
                print(f"  [{intento}/{max_iter}] n_est={p['n_est']} "
                      f"depth={str(p['depth']):<4} | "
                      f"result={res['acc_result']:.4f} "
                      f"series={res['acc_series']:.4f}")
    else:
        # ── Paralelo en lotes del tamaño de n_jobs ───────────────────────
        batch_size = n_jobs
        lote_num   = 0

        for start in range(0, max_iter, batch_size):
            lote       = params_list[start: start + batch_size]
            lote_num  += 1
            resultados = jl.Parallel(n_jobs=n_jobs, prefer="threads")(
                jl.delayed(_una_iteracion)(
                    p["seed"], p["n_est"], p["depth"], p["split"], test_size,
                    X, y_miles, y_centenas, y_decenas, y_unidades, y_series,
                )
                for p in lote
            )

            hubo_mejora = False
            for i, res in enumerate(resultados):
                intento = start + i + 1
                mejorado = _actualizar_mejor(
                    res, mejor_acc_result, mejor_acc_series,
                    mejor_modelo_result, mejor_modelo_series, X,
                )
                marcas = ""
                if mejorado[0] > mejor_acc_result:
                    marcas += " ★result"
                    hubo_mejora = True
                if mejorado[1] > mejor_acc_series:
                    marcas += " ★series"
                    hubo_mejora = True

                mejor_acc_result, mejor_acc_series, \
                mejor_modelo_result, mejor_modelo_series = mejorado

                if verbose:
                    print(f"  [{intento}/{max_iter}] n_est={res['n_est']} "
                          f"depth={str(res['depth']):<4} | "
                          f"result={res['acc_result']:.4f} "
                          f"series={res['acc_series']:.4f}{marcas}")

            # ── Early stopping ────────────────────────────────────────────
            if not hubo_mejora:
                sin_mejora += batch_size
            else:
                sin_mejora = 0

            if sin_mejora >= patience:
                if verbose:
                    print(f"\n  ⏹ Early stop: sin mejora en {sin_mejora} iteraciones.")
                break

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


def _actualizar_mejor(res, mejor_acc_result, mejor_acc_series,
                      mejor_modelo_result, mejor_modelo_series, X):
    """Actualiza los mejores modelos si la iteración mejoró."""
    if res["acc_result"] > mejor_acc_result:
        mejor_acc_result    = res["acc_result"]
        mejor_modelo_result = _ModeloCompuesto(
            res["m_m"], res["m_c"], res["m_d"], res["m_u"], X.shape[1]
        )
    if res["acc_series"] > mejor_acc_series:
        mejor_acc_series    = res["acc_series"]
        mejor_modelo_series = res["m_s"]
    return mejor_acc_result, mejor_acc_series, mejor_modelo_result, mejor_modelo_series
