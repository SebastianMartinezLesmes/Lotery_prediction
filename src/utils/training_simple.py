"""
Entrenamiento simplificado: predice cada dígito del número por separado.
- 4 modelos para result (miles, centenas, decenas, unidades)
- 1 modelo para series (12 clases zodiacales)

Modos:
  test  → 2 iteraciones, árboles pequeños, verificación rápida
  prod  → 30 iteraciones, búsqueda amplia de hiperparámetros
"""
import os
import joblib
import warnings
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from src.utils.save_training import guardar_modelo_si_mejora, crear_base_modelos_IA

warnings.filterwarnings("ignore")


# ============================================================
# Modelo compuesto: 4 RF (uno por dígito) en un solo objeto
# ============================================================

class _ModeloCompuesto:
    """
    Encapsula 4 modelos de dígitos.
    - predict()          → reconstruye el número completo
    - top3_numeros()     → top 3 combinaciones más probables
    """
    def __init__(self, miles, centenas, decenas, unidades, n_features_in_):
        self.miles          = miles
        self.centenas       = centenas
        self.decenas        = decenas
        self.unidades       = unidades
        self.n_features_in_ = n_features_in_

    def predict(self, X):
        m = self.miles.predict(X)
        c = self.centenas.predict(X)
        d = self.decenas.predict(X)
        u = self.unidades.predict(X)
        return m * 1000 + c * 100 + d * 10 + u

    def top3_numeros(self, X):
        """Genera top 3 números combinando probabilidades de cada dígito."""
        def top_k(model, k=2):
            p   = model.predict_proba(X)[0]
            idx = np.argsort(p)[-k:][::-1]
            return [(int(model.classes_[i]), float(p[i])) for i in idx]

        t_m = top_k(self.miles)
        t_c = top_k(self.centenas)
        t_d = top_k(self.decenas)
        t_u = top_k(self.unidades)

        candidatos = [
            (m*1000 + c*100 + d*10 + u, pm * pc * pd * pu)
            for m, pm in t_m
            for c, pc in t_c
            for d, pd in t_d
            for u, pu in t_u
        ]
        candidatos.sort(key=lambda x: x[1], reverse=True)
        return candidatos[:3]


# ============================================================
# Función de entrenamiento RF rápido
# ============================================================

def _entrenar_rf(X_train, y_train, X_test, y_test,
                 n_estimators=100, max_depth=6, seed=42, min_samples_split=4):
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        class_weight="balanced",
        random_state=seed,
        n_jobs=1
    )
    model.fit(X_train, y_train)
    acc = accuracy_score(y_test, model.predict(X_test))
    return model, acc


# ============================================================
# Entrenamiento principal con loop de mejora
# ============================================================

def entrenar_modelos_por_loteria(
    X, y_result, y_series,
    nombre_loteria,
    min_acc=None,
    max_iter=None,
    verbose=True,
):
    """
    Entrena modelos para una lotería con loop de mejora iterativo.

    Los parámetros min_acc y max_iter se toman del perfil activo
    (settings.TRAINING_MODE = 'test' | 'prod') si no se pasan explícitamente.

    Estrategia:
    - Descompone el número en 4 dígitos (miles, centenas, decenas, unidades)
    - Entrena un RF por dígito (10 clases c/u en vez de 909)
    - Repite max_iter veces con distintos seeds e hiperparámetros
    - Guarda solo si supera el modelo previo en IA_models/
    """
    from src.core.config import settings

    profile   = settings.get_training_profile()
    min_acc   = min_acc  if min_acc  is not None else profile["min_accuracy"]
    max_iter  = max_iter if max_iter is not None else profile["max_iter"]
    test_size = profile["test_size"]

    # Espacio de búsqueda según perfil
    n_est_options   = profile["n_estimators"]
    depth_options   = profile["max_depth"]
    split_options   = profile["min_samples_split"]

    mode_label = settings.TRAINING_MODE.upper()

    if verbose:
        print(f"\n{'='*60}")
        print(f"Modo: {mode_label}  |  Entrenando: {nombre_loteria.upper()}")
        print(f"Registros: {len(X)} | Features: {X.shape[1]}")
        print(f"Clases result únicas: {len(np.unique(y_result))}")
        print(f"Clases series únicas: {len(np.unique(y_series))}")
        print(f"Iteraciones: {max_iter}  |  test_size: {test_size}")
        print(f"n_estimators: {n_est_options}")
        print(f"max_depth: {depth_options}")
        print('='*60)

    # Descomponer número en dígitos
    y_miles    = (y_result // 1000) % 10
    y_centenas = (y_result // 100)  % 10
    y_decenas  = (y_result // 10)   % 10
    y_unidades =  y_result          % 10

    # Inicializar con baseline de modelos previos
    mejor_acc_result    = -1.0
    mejor_acc_series    = -1.0
    mejor_modelo_result = None
    mejor_modelo_series = None

    base = crear_base_modelos_IA(nombre_loteria)
    for path in base["result"]:
        if os.path.exists(path):
            try:
                payload = joblib.load(path)
                acc = payload.get("accuracy", 0)
                if acc > mejor_acc_result:
                    mejor_acc_result    = acc
                    mejor_modelo_result = payload["model"]
                    if verbose:
                        print(f"✓ Result previo cargado (baseline: {acc:.4f})")
            except Exception:
                pass

    for path in base["series"]:
        if os.path.exists(path):
            try:
                payload = joblib.load(path)
                acc = payload.get("accuracy", 0)
                if acc > mejor_acc_series:
                    mejor_acc_series    = acc
                    mejor_modelo_series = payload["model"]
                    if verbose:
                        print(f"✓ Series previo cargado (baseline: {acc:.4f})")
            except Exception:
                pass

    # Loop de mejora
    for intento in range(1, max_iter + 1):
        seed  = np.random.randint(0, 10000)
        n_est = int(np.random.choice(n_est_options))
        depth = np.random.choice(depth_options)
        split = int(np.random.choice(split_options))

        X_tr, X_te, \
        ym_tr, ym_te, \
        yc_tr, yc_te, \
        yd_tr, yd_te, \
        yu_tr, yu_te, \
        ys_tr, ys_te = train_test_split(
            X, y_miles, y_centenas, y_decenas, y_unidades, y_series,
            test_size=test_size, random_state=seed
        )

        m_m, acc_m = _entrenar_rf(X_tr, ym_tr, X_te, ym_te, n_est, depth, seed, split)
        m_c, acc_c = _entrenar_rf(X_tr, yc_tr, X_te, yc_te, n_est, depth, seed, split)
        m_d, acc_d = _entrenar_rf(X_tr, yd_tr, X_te, yd_te, n_est, depth, seed, split)
        m_u, acc_u = _entrenar_rf(X_tr, yu_tr, X_te, yu_te, n_est, depth, seed, split)
        m_s, acc_s = _entrenar_rf(X_tr, ys_tr, X_te, ys_te, n_est, depth, seed, split)

        acc_result = (acc_m + acc_c + acc_d + acc_u) / 4

        marcas = ""
        if acc_result > mejor_acc_result:
            mejor_acc_result    = acc_result
            mejor_modelo_result = _ModeloCompuesto(m_m, m_c, m_d, m_u, X.shape[1])
            marcas += " ★result"
        if acc_s > mejor_acc_series:
            mejor_acc_series    = acc_s
            mejor_modelo_series = m_s
            marcas += " ★series"

        if verbose:
            print(f"  [{intento}/{max_iter}] n_est={n_est} depth={str(depth):<4} "
                  f"| result={acc_result:.4f} series={acc_s:.4f}{marcas}")

    if verbose:
        print(f"\n  Mejor result acc : {mejor_acc_result:.4f}")
        print(f"  Mejor series acc : {mejor_acc_series:.4f}")

    # Guardar en memoria IA
    print("\n🧠 Guardando en memoria IA:")
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="result",
        modelo=mejor_modelo_result,
        accuracy=mejor_acc_result,
        n_records=len(X)
    )
    guardar_modelo_si_mejora(
        nombre_loteria=nombre_loteria,
        tipo_modelo="series",
        modelo=mejor_modelo_series,
        accuracy=mejor_acc_series,
        n_records=len(X)
    )

    if verbose:
        print(f"\n✅ Entrenamiento completado")
        print(f"   Mejor result acc: {mejor_acc_result:.4f}")
        print(f"   Mejor series acc: {mejor_acc_series:.4f}")

    return mejor_modelo_result, mejor_modelo_series
