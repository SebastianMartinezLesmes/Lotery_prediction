"""
Backtesting del modelo de predicción — evaluación sorteo por sorteo.

Simula condiciones de producción: para cada sorteo de la ventana de test,
el modelo solo puede ver el historial acumulado hasta ese momento (sin ver
el futuro). Mide las métricas reales de predicción.

Uso:
    # Backtest rápido (modo test, sin re-entrenamiento)
    python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100

    # Con re-entrenamiento periódico
    python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100 --reentrenar 30

    # Solo evaluar con modelos ya entrenados
    python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100 --solo-evaluar
"""
import os
import sys
import argparse
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Añadir raíz del proyecto al path ─────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Importaciones del proyecto ────────────────────────────────────────────────
os.environ["TRAINING_MODE"] = "test"

from src.features.feature_engineering import generar_features, FEATURE_COLUMNS
from src.utils.training_simple import entrenar_modelos_por_loteria, _ModeloCompuesto
from src.utils.prediction import buscar_mejor_modelo
from src.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────

def cargar_datos(loteria: str) -> pd.DataFrame:
    """Carga datos desde Neon o fallback Excel, filtrados por lotería."""
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
# Entrenamiento con slot _backtest
# ─────────────────────────────────────────────────────────────────────────────

def entrenar_backtest(df_train: pd.DataFrame, nombre_slot: str, verbose: bool = True):
    """
    Entrena el modelo con df_train usando el pipeline estándar.
    Guarda modelos con nombre_slot para no afectar producción.
    Retorna (modelo_result, modelo_series).
    """
    X_df = generar_features(df_train)
    df_alineado = df_train.loc[X_df.index]
    X = X_df.values
    y_result = df_alineado["result"].values
    y_series = pd.Categorical(
        df_alineado["series"].astype(str).str.upper(),
        categories=settings.SIGNOS
    ).codes.values

    modelo_result, modelo_series = entrenar_modelos_por_loteria(
        X, y_result, y_series,
        nombre_loteria=nombre_slot,
        verbose=verbose,
    )
    return modelo_result, modelo_series


def cargar_modelos_backtest(nombre_slot: str):
    """Carga los mejores modelos guardados con el slot de backtesting."""
    _, payload_r, _ = buscar_mejor_modelo(nombre_slot, "result")
    _, payload_s, _ = buscar_mejor_modelo(nombre_slot, "series")

    modelo_result = payload_r["model"] if payload_r else None
    modelo_series = payload_s["model"] if payload_s else None
    return modelo_result, modelo_series


# ─────────────────────────────────────────────────────────────────────────────
# Predicción con top-3
# ─────────────────────────────────────────────────────────────────────────────

def predecir(modelo_result, modelo_series, features: np.ndarray):
    """
    Retorna top3_numeros y top3_signos dados los features (1 fila).
    """
    if modelo_result is None or modelo_series is None:
        return [], []

    # top3 números
    if isinstance(modelo_result, _ModeloCompuesto):
        top3_numeros = modelo_result.top3_numeros(features)
    elif hasattr(modelo_result, "predict_proba"):
        probs = modelo_result.predict_proba(features)[0]
        idx = np.argsort(probs)[-3:][::-1]
        top3_numeros = [(int(modelo_result.classes_[i]), float(probs[i])) for i in idx]
    else:
        pred = int(modelo_result.predict(features)[0])
        top3_numeros = [(pred, 1.0)]

    # top3 signos
    if hasattr(modelo_series, "predict_proba"):
        probs_s = modelo_series.predict_proba(features)[0]
        idx_s = np.argsort(probs_s)[-3:][::-1]
        top3_signos = [(int(modelo_series.classes_[i]), float(probs_s[i])) for i in idx_s]
    else:
        pred_s = int(modelo_series.predict(features)[0])
        top3_signos = [(pred_s, 1.0)]

    return top3_numeros, top3_signos


# ─────────────────────────────────────────────────────────────────────────────
# Obtener features para el sorteo i (estado antes del sorteo i)
# ─────────────────────────────────────────────────────────────────────────────

def obtener_features_para_sorteo(df_acumulado: pd.DataFrame) -> np.ndarray:
    """
    En backtesting evaluamos el sorteo YA CONOCIDO usando el historial
    acumulado hasta el momento justo antes de ese sorteo.
    Retorna la última fila de generar_features(df_acumulado).
    """
    X_df = generar_features(df_acumulado)
    if len(X_df) == 0:
        return None
    return X_df.tail(1).values


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Backtesting sorteo-a-sorteo con ventana deslizante"
    )
    parser.add_argument(
        "--lottery", default="ASTRO LUNA",
        help="Nombre de la lotería (default: 'ASTRO LUNA')"
    )
    parser.add_argument(
        "--ventana", type=int, default=100,
        help="Número de sorteos reservados para evaluar (default: 100)"
    )
    parser.add_argument(
        "--reentrenar", type=int, default=None, metavar="N",
        help="Re-entrenar cada N sorteos nuevos (opcional)"
    )
    parser.add_argument(
        "--solo-evaluar", action="store_true",
        help="Solo evaluar con modelos ya entrenados, sin re-entrenar"
    )
    args = parser.parse_args()

    loteria  = args.lottery
    ventana  = args.ventana
    reentrenar_cada = args.reentrenar
    solo_evaluar    = args.solo_evaluar
    nombre_slot = loteria + "_backtest"

    print(f"\n{'='*60}")
    print(f"BACKTESTING — {loteria.upper()}")
    print(f"{'='*60}")
    print(f"Ventana test    : {ventana} sorteos")
    print(f"Re-entrenamiento: {reentrenar_cada if reentrenar_cada else 'NO'}")
    print(f"Solo evaluar    : {solo_evaluar}")
    print(f"Slot modelos    : {nombre_slot}")

    # ── 1. Cargar datos ───────────────────────────────────────────────────
    df = cargar_datos(loteria)
    if len(df) < ventana + 50:
        print(f"[ERROR] Datos insuficientes: {len(df)} registros (mínimo {ventana + 50})")
        sys.exit(1)

    # ── 2. Separar train base y ventana test ──────────────────────────────
    df_train_base = df.iloc[:-ventana].copy().reset_index(drop=True)
    df_test       = df.iloc[-ventana:].copy().reset_index(drop=True)

    print(f"\nHistorial total  : {len(df)} sorteos")
    print(f"Train inicial    : {len(df_train_base)} sorteos")
    print(f"Ventana test     : {len(df_test)} sorteos")

    # ── 3. Entrenamiento inicial ──────────────────────────────────────────
    if solo_evaluar:
        print(f"\n[INFO] Modo --solo-evaluar: cargando modelos existentes...")
        modelo_result, modelo_series = cargar_modelos_backtest(nombre_slot)
        if modelo_result is None or modelo_series is None:
            print(f"[ERROR] No se encontraron modelos para '{nombre_slot}'.")
            print(f"        Ejecute primero sin --solo-evaluar para entrenar.")
            sys.exit(1)
        print(f"[INFO] Modelos cargados.")
    else:
        print(f"\nEntrenamiento inicial con {len(df_train_base)} sorteos...")
        modelo_result, modelo_series = entrenar_backtest(df_train_base, nombre_slot, verbose=True)

    # ── 4. Loop sorteo por sorteo ─────────────────────────────────────────
    print(f"\nEvaluando {len(df_test)} sorteos (ventana deslizante)...")
    resultados = []

    for i in range(len(df_test)):
        # Historial acumulado hasta justo ANTES del sorteo i
        df_acumulado = pd.concat(
            [df_train_base, df_test.iloc[:i]],
            ignore_index=True
        )
        df_acumulado["fecha"] = pd.to_datetime(df_acumulado["fecha"])

        # Generar features
        features = obtener_features_para_sorteo(df_acumulado)
        if features is None:
            continue

        # Resultado real del sorteo i
        real_result = int(df_test.iloc[i]["result"])
        real_series = str(df_test.iloc[i]["series"]).upper()

        # Predicción
        top3_numeros, top3_signos = predecir(modelo_result, modelo_series, features)

        if not top3_numeros:
            continue

        pred_top1_num   = top3_numeros[0][0]
        real_en_top3    = real_result in [n for n, _ in top3_numeros]

        # El modelo de series predice el código numérico del signo
        pred_top1_codigo = top3_signos[0][0] if top3_signos else -1

        # Convertir código de series predicho a nombre para comparar
        try:
            pred_signo = settings.SIGNOS[pred_top1_codigo]
        except (IndexError, TypeError):
            pred_signo = str(pred_top1_codigo)

        series_ok = (real_series == pred_signo)

        resultados.append({
            "fecha":        df_test.iloc[i]["fecha"],
            "real_result":  real_result,
            "pred_top1":    pred_top1_num,
            "real_en_top3": real_en_top3,
            "real_series":  real_series,
            "series_ok":    series_ok,
            "miles_ok":     (real_result // 1000) % 10 == (pred_top1_num // 1000) % 10,
            "centenas_ok":  (real_result // 100)  % 10 == (pred_top1_num // 100)  % 10,
            "decenas_ok":   (real_result // 10)   % 10 == (pred_top1_num // 10)   % 10,
            "unidades_ok":   real_result % 10            == pred_top1_num % 10,
        })

        # Re-entrenamiento periódico
        if reentrenar_cada and i > 0 and i % reentrenar_cada == 0:
            print(f"\n  [Re-entrenamiento en sorteo {i}/{len(df_test)}]")
            df_acum_retrain = pd.concat(
                [df_train_base, df_test.iloc[:i + 1]],
                ignore_index=True
            )
            modelo_result, modelo_series = entrenar_backtest(
                df_acum_retrain, nombre_slot, verbose=False
            )

        if (i + 1) % 20 == 0:
            print(f"  Sorteo {i+1}/{len(df_test)} evaluado...")

    # ── 5. Calcular métricas ──────────────────────────────────────────────
    if not resultados:
        print("[ERROR] No se generaron resultados. Verifique los datos.")
        sys.exit(1)

    df_res = pd.DataFrame(resultados)
    N = len(df_res)

    acierto_exacto  = df_res["pred_top1"].eq(df_res["real_result"]).mean()
    real_en_top3    = df_res["real_en_top3"].mean()
    acierto_serie   = df_res["series_ok"].mean()
    acc_miles       = df_res["miles_ok"].mean()
    acc_centenas    = df_res["centenas_ok"].mean()
    acc_decenas     = df_res["decenas_ok"].mean()
    acc_unidades    = df_res["unidades_ok"].mean()

    # Líneas de referencia
    AZAR_EXACTO = 1.0 / 9999   # aprox 0.01%
    LAG1_EXACTO = 0.0502        # repetir número anterior

    mejora_vs_azar  = acierto_exacto / AZAR_EXACTO if AZAR_EXACTO > 0 else 0
    mejora_vs_lag1  = acierto_exacto / LAG1_EXACTO if LAG1_EXACTO > 0 else 0

    # Intervalos de confianza (95%) para proporciones
    def ic95(p, n):
        return 1.96 * np.sqrt(p * (1 - p) / n) if n > 0 else 0

    ic_exacto   = ic95(acierto_exacto, N)
    ic_top3     = ic95(real_en_top3,   N)
    ic_serie    = ic95(acierto_serie,  N)
    ic_miles    = ic95(acc_miles,      N)
    ic_centenas = ic95(acc_centenas,   N)
    ic_decenas  = ic95(acc_decenas,    N)
    ic_unidades = ic95(acc_unidades,   N)

    # ── 6. Guardar CSV ────────────────────────────────────────────────────
    csv_path = os.path.join(_ROOT, "data", "backtesting_results.csv")
    df_res.to_csv(csv_path, index=False)
    print(f"\n[INFO] Resultados guardados en: {csv_path}")

    # ── 7. Imprimir resumen ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"=== BACKTESTING RESULTS — {loteria.upper()} ===")
    print(f"{'='*60}")
    print(f"Sorteos evaluados      : {N}")
    print(f"Acierto exacto (top1)  : {acierto_exacto:.2%}  ± {ic_exacto:.2%}")
    print(f"Real en top-3          : {real_en_top3:.2%}  ± {ic_top3:.2%}")
    print(f"Acierto signo          : {acierto_serie:.2%}  ± {ic_serie:.2%}")
    print()
    print(f"Acierto por dígito:")
    print(f"  Miles                : {acc_miles:.2%}  ± {ic_miles:.2%}")
    print(f"  Centenas             : {acc_centenas:.2%}  ± {ic_centenas:.2%}")
    print(f"  Decenas              : {acc_decenas:.2%}  ± {ic_decenas:.2%}")
    print(f"  Unidades             : {acc_unidades:.2%}  ± {ic_unidades:.2%}")
    print()
    print(f"Comparación con líneas de referencia:")
    print(f"  Mejora vs azar puro  : {mejora_vs_azar:.1f}x")
    print(f"  Mejora vs lag1       : {mejora_vs_lag1:.2f}x")
    print()
    print(f"Criterio de éxito:")
    print(f"  real_en_top3 > 10%   : {'OK' if real_en_top3 > 0.10 else 'NO'} ({real_en_top3:.2%})")
    print(f"  acierto_serie > 15%  : {'OK' if acierto_serie > 0.15 else 'NO'} ({acierto_serie:.2%})")
    print(f"  acc_unidades > 20%   : {'OK' if acc_unidades > 0.20 else 'NO'} ({acc_unidades:.2%})")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
