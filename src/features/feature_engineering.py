"""
Feature engineering basado exclusivamente en el historial de resultados.

No se usan features de calendario (dia, mes, anio, etc.) porque la fecha
no tiene relación causal con el resultado de la lotería.

Decisiones basadas en análisis estadístico de los datos:
  - Autocorr result lag1      ≈ 0.07  → señal débil pero presente
  - Autocorr diff   lag1      ≈ -0.46 → señal fuerte: reversión a la media
  - Autocorr dígito unidades  ≈ 0.08  → leve persistencia por posición
  - Correlación entre dígitos ≈ ~0    → dígitos son independientes entre sí
  - Suma de dígitos autocorr  ≈ 0.05  → señal débil pero captura nivel general
"""
import numpy as np
import pandas as pd

# ── Columnas canónicas ────────────────────────────────────────────────────
FEATURE_COLUMNS = [
    # ── Lags del resultado completo ──────────────────────────────────────
    "result_lag_1",
    "result_lag_2",
    "result_lag_3",
    "result_lag_5",
    "result_lag_7",

    # ── Dígitos de los últimos 3 resultados ──────────────────────────────
    # Permite al modelo aprender patrones por posición de dígito
    "lag1_miles",    "lag1_centenas",    "lag1_decenas",    "lag1_unidades",
    "lag2_miles",    "lag2_centenas",    "lag2_decenas",    "lag2_unidades",
    "lag3_miles",    "lag3_centenas",    "lag3_decenas",    "lag3_unidades",

    # ── Diferencias (reversión a la media — autocorr = -0.46) ────────────
    "diff_1",           # result[i] - result[i-1]
    "diff_2",           # result[i-1] - result[i-2]
    "diff_abs_1",       # magnitud del último cambio
    "signo_diff_1",     # dirección: +1 subió, -1 bajó, 0 igual

    # ── Racha direccional ────────────────────────────────────────────────
    # Cuántos sorteos consecutivos el resultado viene subiendo (+) o bajando (-)
    "racha",

    # ── Rolling stats del resultado ──────────────────────────────────────
    "rolling_mean_7",
    "rolling_std_7",
    "rolling_mean_30",
    "rolling_std_30",
    "rolling_max_7",
    "rolling_min_7",
    "rolling_range_7",  # dispersión reciente

    # ── Posición relativa respecto a la media ────────────────────────────
    "lag1_sobre_media_7",   # 1 si lag1 > media de los últimos 7
    "lag1_sobre_media_30",  # 1 si lag1 > media de los últimos 30
    "lag1_z_score_30",      # cuántas desv. std está lag1 respecto a media30

    # ── Tendencia ────────────────────────────────────────────────────────
    "tendencia_7",          # 1 si último > primero en ventana 7
    "tendencia_30",

    # ── Suma de dígitos ──────────────────────────────────────────────────
    # Captura el "nivel" general del número (bajo=0-9, alto=28-36)
    "lag1_suma_digitos",
    "lag1_suma_digitos_par",   # 1 si la suma es par

    # ── Paridad de dígitos ───────────────────────────────────────────────
    "lag1_unidades_par",    # 1 si unidades del último resultado es par

    # ── Frecuencia histórica del número exacto ───────────────────────────
    "freq_10",
    "freq_30",
    "freq_90",

    # ── Tiempo sin aparecer ──────────────────────────────────────────────
    "dias_desde_ultimo",
]


def generar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera el vector de features para cada fila del historial.

    Args:
        df: DataFrame con columnas [fecha, result]. Debe estar ordenado por fecha.

    Returns:
        DataFrame con FEATURE_COLUMNS como columnas, mismo largo que df tras fillna.
    """
    df = df.sort_values("fecha").copy().reset_index(drop=True)
    r = df["result"]

    # ── Lags ─────────────────────────────────────────────────────────────
    df["result_lag_1"] = r.shift(1)
    df["result_lag_2"] = r.shift(2)
    df["result_lag_3"] = r.shift(3)
    df["result_lag_5"] = r.shift(5)
    df["result_lag_7"] = r.shift(7)

    # ── Dígitos de los lags ──────────────────────────────────────────────
    for lag_n in [1, 2, 3]:
        col = f"result_lag_{lag_n}"
        v = df[col].fillna(0).astype(int)
        df[f"lag{lag_n}_miles"]    = (v // 1000) % 10
        df[f"lag{lag_n}_centenas"] = (v // 100)  % 10
        df[f"lag{lag_n}_decenas"]  = (v // 10)   % 10
        df[f"lag{lag_n}_unidades"] =  v           % 10

    # ── Diferencias ──────────────────────────────────────────────────────
    df["diff_1"]      = r.diff(1)
    df["diff_2"]      = r.diff(1).shift(1)   # diff del sorteo anterior
    df["diff_abs_1"]  = df["diff_1"].abs()
    df["signo_diff_1"] = np.sign(df["diff_1"])

    # ── Racha ─────────────────────────────────────────────────────────────
    rachas = [0]
    diffs = r.diff().fillna(0).values
    racha_actual = 0
    for d in diffs[1:]:
        if d > 0:
            racha_actual = racha_actual + 1 if racha_actual > 0 else 1
        elif d < 0:
            racha_actual = racha_actual - 1 if racha_actual < 0 else -1
        else:
            racha_actual = 0
        rachas.append(racha_actual)
    df["racha"] = rachas

    # ── Rolling stats ─────────────────────────────────────────────────────
    df["rolling_mean_7"]  = r.rolling(7,  min_periods=1).mean()
    df["rolling_std_7"]   = r.rolling(7,  min_periods=1).std()
    df["rolling_mean_30"] = r.rolling(30, min_periods=1).mean()
    df["rolling_std_30"]  = r.rolling(30, min_periods=1).std()
    df["rolling_max_7"]   = r.rolling(7,  min_periods=1).max()
    df["rolling_min_7"]   = r.rolling(7,  min_periods=1).min()
    df["rolling_range_7"] = df["rolling_max_7"] - df["rolling_min_7"]

    # ── Posición relativa ─────────────────────────────────────────────────
    lag1 = df["result_lag_1"].fillna(0)
    df["lag1_sobre_media_7"]  = (lag1 > df["rolling_mean_7"].shift(1).fillna(0)).astype(int)
    df["lag1_sobre_media_30"] = (lag1 > df["rolling_mean_30"].shift(1).fillna(0)).astype(int)
    std30 = df["rolling_std_30"].shift(1).fillna(1).replace(0, 1)
    df["lag1_z_score_30"] = (lag1 - df["rolling_mean_30"].shift(1).fillna(0)) / std30

    # ── Tendencia ─────────────────────────────────────────────────────────
    def _tendencia(series, window):
        return (
            series.rolling(window, min_periods=2)
            .apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else 0, raw=False)
        )

    df["tendencia_7"]  = _tendencia(r, 7)
    df["tendencia_30"] = _tendencia(r, 30)

    # ── Suma y paridad de dígitos del lag1 ───────────────────────────────
    v1 = df["result_lag_1"].fillna(0).astype(int)
    suma = (v1 // 1000) % 10 + (v1 // 100) % 10 + (v1 // 10) % 10 + v1 % 10
    df["lag1_suma_digitos"]     = suma
    df["lag1_suma_digitos_par"] = (suma % 2 == 0).astype(int)
    df["lag1_unidades_par"]     = (v1 % 10 % 2 == 0).astype(int)

    # ── Frecuencia histórica del número exacto ────────────────────────────
    def _freq_ventana(vals: np.ndarray, ventana: int) -> list:
        result = []
        for i in range(len(vals)):
            inicio = max(0, i - ventana)
            result.append(int((vals[inicio:i] == vals[i]).sum()))
        return result

    arr = r.values
    df["freq_10"] = _freq_ventana(arr, 10)
    df["freq_30"] = _freq_ventana(arr, 30)
    df["freq_90"] = _freq_ventana(arr, 90)

    # ── Días desde la última aparición del mismo número ───────────────────
    last_seen: dict = {}
    dias_desde = []
    for _, row in df.iterrows():
        n = row["result"]
        if n in last_seen:
            dias_desde.append((row["fecha"] - last_seen[n]).days)
        else:
            dias_desde.append(0)
        last_seen[n] = row["fecha"]
    df["dias_desde_ultimo"] = dias_desde

    # ── Limpiar y retornar ────────────────────────────────────────────────
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

    return df[FEATURE_COLUMNS]
