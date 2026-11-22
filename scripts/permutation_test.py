"""
Prueba de permutación: mide si el modelo tiene señal real sobre el azar.

Para cada dígito (Miles, Centenas, Decenas, Unidades) y el Signo:
  1. Entrena el modelo REAL con los datos de entrenamiento.
  2. Evalúa accuracy en el bloque test → acc_real.
  3. Repite 30 veces: baraja y_train de forma independiente, re-entrena,
     evalúa en test → acc_shuffled.
  4. p-valor = proporción de runs donde acc_shuffled >= acc_real.
  5. Si p < 0.05, el modelo tiene señal estadística ('** señal').

Uso:
    python scripts/permutation_test.py --lottery "ASTRO LUNA"
"""
import os
import sys
import argparse
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings("ignore")

# ── Añadir raíz del proyecto al path ─────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Importaciones del proyecto ────────────────────────────────────────────────
os.environ["TRAINING_MODE"] = "test"

from src.features.feature_engineering import generar_features, FEATURE_COLUMNS
from src.utils.training_simple import _evaluar_individuo, _ModeloCompuesto
from sklearn.metrics import accuracy_score


# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────

def cargar_datos(loteria: str) -> pd.DataFrame:
    """Carga datos desde Neon o fallback Excel."""
    df = None

    # Intentar Neon
    try:
        from src.database.connection import NeonConnection
        from src.database.repository import LotteriaRepository
        conn = NeonConnection()
        try:
            repo = LotteriaRepository(conn)
            df = repo.get_all_results(loteria)
        finally:
            conn.close()
        if df is not None and not df.empty:
            print(f"[INFO] Datos cargados desde Neon: {len(df)} registros")
    except Exception as e:
        print(f"[WARN] Neon no disponible, usando Excel fallback: {e}")

    # Fallback Excel
    if df is None or df.empty:
        excel_path = os.path.join(_ROOT, "data", "resultados_astro.xlsx")
        df = pd.read_excel(excel_path)
        df = df.rename(columns=lambda c: c.strip().lower())
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["result"] = df["result"].astype(int)
        df["series"] = df["series"].astype(str).str.upper()
        df = df[df["lottery"].str.upper() == loteria.upper()].copy()
        df = df.sort_values("fecha").reset_index(drop=True)
        print(f"[INFO] Datos cargados desde Excel: {len(df)} registros")

    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df[df["lottery"].str.upper() == loteria.upper()].copy()
    df = df.sort_values("fecha").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Entrenamiento de un individuo aleatorio (modo test)
# ─────────────────────────────────────────────────────────────────────────────

def _entrenar_rf_simple(X_tr, y_tr, X_te, y_te, seed=42):
    """Entrena un RF simple y retorna (modelo, accuracy)."""
    from sklearn.ensemble import RandomForestClassifier
    m = RandomForestClassifier(
        n_estimators=20,
        max_depth=4,
        min_samples_split=4,
        class_weight="balanced",
        random_state=seed,
        n_jobs=1,
    )
    m.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, m.predict(X_te))
    return m, acc


def _entrenar_y_evaluar(X_tr, X_te,
                        ym_tr, yc_tr, yd_tr, yu_tr, ys_tr,
                        ym_te, yc_te, yd_te, yu_te, ys_te,
                        seed=42):
    """Entrena los 5 modelos y retorna accuracies en test."""
    _, am = _entrenar_rf_simple(X_tr, ym_tr, X_te, ym_te, seed)
    _, ac = _entrenar_rf_simple(X_tr, yc_tr, X_te, yc_te, seed + 1)
    _, ad = _entrenar_rf_simple(X_tr, yd_tr, X_te, yd_te, seed + 2)
    _, au = _entrenar_rf_simple(X_tr, yu_tr, X_te, yu_te, seed + 3)
    _, as_ = _entrenar_rf_simple(X_tr, ys_tr, X_te, ys_te, seed + 4)
    return am, ac, ad, au, as_


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prueba de permutación — señal real vs azar (30 runs)"
    )
    parser.add_argument(
        "--lottery", default="ASTRO LUNA",
        help="Nombre de la lotería (default: 'ASTRO LUNA')"
    )
    args = parser.parse_args()
    loteria = args.lottery

    print(f"\n{'='*60}")
    print(f"PERMUTATION TEST — {loteria.upper()}")
    print(f"{'='*60}")

    # ── 1. Cargar datos ───────────────────────────────────────────────────
    df = cargar_datos(loteria)
    if len(df) < 50:
        print(f"[ERROR] Datos insuficientes: {len(df)} registros")
        sys.exit(1)

    # ── 2. Generar features ───────────────────────────────────────────────
    X_df = generar_features(df)
    df_alineado = df.loc[X_df.index]
    X = X_df.values
    y_result = df_alineado["result"].values

    from src.core.config import settings
    y_series = pd.Categorical(
        df_alineado["series"].astype(str).str.upper(),
        categories=settings.SIGNOS
    ).codes.values

    # ── 3. Split 70/15/15 ────────────────────────────────────────────────
    n = len(X)
    n_test  = int(n * 0.15)
    n_val   = int(n * 0.15)
    n_train = n - n_val - n_test

    X_tr = X[:n_train]
    X_te = X[n_train + n_val:]

    # Dígitos
    y_miles    = (y_result // 1000) % 10
    y_centenas = (y_result // 100)  % 10
    y_decenas  = (y_result // 10)   % 10
    y_unidades =  y_result          % 10

    ym_tr, ym_te = y_miles[:n_train],    y_miles[n_train + n_val:]
    yc_tr, yc_te = y_centenas[:n_train], y_centenas[n_train + n_val:]
    yd_tr, yd_te = y_decenas[:n_train],  y_decenas[n_train + n_val:]
    yu_tr, yu_te = y_unidades[:n_train], y_unidades[n_train + n_val:]
    ys_tr, ys_te = y_series[:n_train],   y_series[n_train + n_val:]

    print(f"\nRegistros totales : {n}")
    print(f"  Train           : {n_train}  ({n_train/n:.0%})")
    print(f"  Val (skip)      : {n_val}   ({n_val/n:.0%})")
    print(f"  Test            : {n_test}  ({n_test/n:.0%})")
    print(f"\nEntrenando modelo real...")

    # ── 4. Accuracy real del modelo ───────────────────────────────────────
    acc_real_m, acc_real_c, acc_real_d, acc_real_u, acc_real_s = _entrenar_y_evaluar(
        X_tr, X_te,
        ym_tr, yc_tr, yd_tr, yu_tr, ys_tr,
        ym_te, yc_te, yd_te, yu_te, ys_te,
        seed=42
    )
    acc_real = {
        "Miles":    acc_real_m,
        "Centenas": acc_real_c,
        "Decenas":  acc_real_d,
        "Unidades": acc_real_u,
        "Signo":    acc_real_s,
    }

    print(f"Modelo real entrenado.")
    print(f"\nEjecutando 30 runs de permutación...")

    # ── 5. Permutación: 30 runs ───────────────────────────────────────────
    N_RUNS = 30
    rng = np.random.default_rng(seed=0)

    shuffled = {t: [] for t in acc_real}

    for run in range(N_RUNS):
        seed_run = int(rng.integers(0, 100_000))

        # Barajar y_train de forma independiente para cada target
        ym_sh = ym_tr.copy(); rng.shuffle(ym_sh)
        yc_sh = yc_tr.copy(); rng.shuffle(yc_sh)
        yd_sh = yd_tr.copy(); rng.shuffle(yd_sh)
        yu_sh = yu_tr.copy(); rng.shuffle(yu_sh)
        ys_sh = ys_tr.copy(); rng.shuffle(ys_sh)

        am, ac, ad, au, as_ = _entrenar_y_evaluar(
            X_tr, X_te,
            ym_sh, yc_sh, yd_sh, yu_sh, ys_sh,
            ym_te, yc_te, yd_te, yu_te, ys_te,
            seed=seed_run
        )
        shuffled["Miles"].append(am)
        shuffled["Centenas"].append(ac)
        shuffled["Decenas"].append(ad)
        shuffled["Unidades"].append(au)
        shuffled["Signo"].append(as_)

        if (run + 1) % 10 == 0:
            print(f"  [{run+1}/{N_RUNS}] completado")

    # ── 6. Calcular p-valores ─────────────────────────────────────────────
    resultados = []
    for target in ["Miles", "Centenas", "Decenas", "Unidades", "Signo"]:
        ar = acc_real[target]
        sh = np.array(shuffled[target])
        pval = (sh >= ar).mean()
        resultados.append((target, ar, sh.mean(), pval))

    # ── 7. Imprimir tabla ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"=== PERMUTATION TEST (30 runs) — {loteria.upper()} ===")
    print(f"{'='*60}")
    print(f"  {'Target':<12} {'Acc_Real':>10} {'Mean_Shuffled':>15} {'p-valor':>10}")
    print(f"  {'-'*12} {'-'*10} {'-'*15} {'-'*10}")
    for target, acc_real_val, mean_shuf, pval in resultados:
        señal = "** señal" if pval < 0.05 else "(sin señal)"
        print(f"  {target:<12} {acc_real_val:>10.2%} {mean_shuf:>15.2%} {pval:>10.3f}  {señal}")
    print(f"{'='*60}")
    print(f"\nInterpretación: p < 0.05 indica señal estadística real (el modelo")
    print(f"supera el rendimiento obtenido con etiquetas aleatorias).")


if __name__ == "__main__":
    main()
