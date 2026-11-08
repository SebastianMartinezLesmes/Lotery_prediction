"""
Feature engineering basado exclusivamente en el historial de resultados.

REGLA ANTI-FUGA: la fila i describe el estado ANTES del sorteo i.
Solo puede usar r[0..i-1]. Nunca r[i].

Cómo se garantiza: todo estadístico "de ventana" se calcula sobre la serie
completa (como si el sorteo j ya hubiera ocurrido) y luego se desplaza una
posición con .shift(1). Así la fila i recibe lo que se sabía tras el sorteo i-1.

No se usan features de calendario: la fecha no tiene relación causal con el
resultado del sorteo.
"""
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    # Lags del resultado completo
    "result_lag_1", "result_lag_2", "result_lag_3", "result_lag_5", "result_lag_7",

    # Dígitos de los últimos 3 resultados
    "lag1_miles", "lag1_centenas", "lag1_decenas", "lag1_unidades",
    "lag2_miles", "lag2_centenas", "lag2_decenas", "lag2_unidades",
    "lag3_miles", "lag3_centenas", "lag3_decenas", "lag3_unidades",

    # Diferencias entre sorteos ya conocidos
    "diff_1",        # r[i-1] - r[i-2]
    "diff_2",        # r[i-2] - r[i-3]
    "diff_abs_1",
    "signo_diff_1",

    # Racha direccional hasta el sorteo i-1
    "racha",

    # Rolling stats hasta el sorteo i-1
    "rolling_mean_7", "rolling_std_7", "rolling_mean_30", "rolling_std_30",
    "rolling_max_7", "rolling_min_7", "rolling_range_7",

    # Posición relativa de lag1 respecto a la media
    "lag1_sobre_media_7", "lag1_sobre_media_30", "lag1_z_score_30",

    # Tendencia hasta el sorteo i-1
    "tendencia_7", "tendencia_30",

    # Suma y paridad de dígitos del lag1
    "lag1_suma_digitos", "lag1_suma_digitos_par", "lag1_unidades_par",

    # Cuántas veces apareció el ÚLTIMO número conocido (lag1) antes de salir
    "freq_lag1_10", "freq_lag1_30", "freq_lag1_90",

    # Días entre la aparición de lag1 y su aparición anterior (-1 = nunca antes)
    "dias_desde_ultimo",
]

MIN_HISTORIAL = 7  # filas iniciales sin historial suficiente (necesita lag_7)


def _racha(r: pd.Series) -> pd.Series:
    out, actual = [0], 0
    for d in r.diff().fillna(0).values[1:]:
        if d > 0:
            actual = actual + 1 if actual > 0 else 1
        elif d < 0:
            actual = actual - 1 if actual < 0 else -1
        else:
            actual = 0
        out.append(actual)
    return pd.Series(out, index=r.index)


def _freq_previa(vals: np.ndarray, ventana: int) -> np.ndarray:
    """Para cada j: veces que vals[j] apareció en vals[j-ventana:j] (solo pasado)."""
    out = np.zeros(len(vals))
    for j in range(len(vals)):
        if np.isnan(vals[j]):
            out[j] = np.nan
            continue
        out[j] = (vals[max(0, j - ventana):j] == vals[j]).sum()
    return out


def _dias_desde_previa(fechas: pd.Series, vals: np.ndarray) -> np.ndarray:
    """Para cada j: días desde la aparición anterior de vals[j]; -1 si nunca."""
    last, out = {}, np.zeros(len(vals))
    for j, (f, n) in enumerate(zip(fechas, vals)):
        if np.isnan(n):
            out[j] = np.nan
            continue
        out[j] = (f - last[n]).days if n in last else -1
        last[n] = f
    return out


def generar_features(df: pd.DataFrame, eliminar_incompletas: bool = True) -> pd.DataFrame:
    """
    Args:
        df: columnas [fecha, result], una fila por sorteo.
        eliminar_incompletas: si True, descarta las primeras MIN_HISTORIAL filas.

    Returns:
        DataFrame con FEATURE_COLUMNS. El índice es la posición del sorteo
        (tras ordenar por fecha y reset_index), por lo que el objetivo
        correspondiente es siempre df_ordenado.loc[X.index, "result"].
    """
    df = df.sort_values("fecha").reset_index(drop=True).copy()
    r = df["result"].astype(float)

    f = pd.DataFrame(index=df.index)

    # ── Lags (ya usan solo el pasado) ────────────────────────────────────
    for k in (1, 2, 3, 5, 7):
        f[f"result_lag_{k}"] = r.shift(k)

    for k in (1, 2, 3):
        v = f[f"result_lag_{k}"].fillna(0).astype(int)
        f[f"lag{k}_miles"] = (v // 1000) % 10
        f[f"lag{k}_centenas"] = (v // 100) % 10
        f[f"lag{k}_decenas"] = (v // 10) % 10
        f[f"lag{k}_unidades"] = v % 10

    # ── Estadísticos "hasta j" calculados sobre r y desplazados 1 ────────
    d1 = r.diff(1)
    base = pd.DataFrame(index=df.index)
    base["diff_1"] = d1
    base["diff_2"] = d1.shift(1)
    base["diff_abs_1"] = d1.abs()
    base["signo_diff_1"] = np.sign(d1)
    base["racha"] = _racha(r)
    for w in (7, 30):
        base[f"rolling_mean_{w}"] = r.rolling(w, min_periods=1).mean()
        base[f"rolling_std_{w}"] = r.rolling(w, min_periods=1).std()
    base["rolling_max_7"] = r.rolling(7, min_periods=1).max()
    base["rolling_min_7"] = r.rolling(7, min_periods=1).min()
    base["rolling_range_7"] = base["rolling_max_7"] - base["rolling_min_7"]

    def _tend(series, w):
        return series.rolling(w, min_periods=2).apply(
            lambda x: 1.0 if x.iloc[-1] > x.iloc[0] else 0.0, raw=False)
    base["tendencia_7"] = _tend(r, 7)
    base["tendencia_30"] = _tend(r, 30)

    arr = r.values
    for w in (10, 30, 90):
        base[f"freq_lag1_{w}"] = _freq_previa(arr, w)
    base["dias_desde_ultimo"] = _dias_desde_previa(df["fecha"], arr)

    base = base.shift(1)          # <- punto clave anti-fuga
    for c in base.columns:
        f[c] = base[c]

    # ── Posición relativa (lag1 vs estadísticos ya desplazados) ──────────
    lag1 = f["result_lag_1"]
    f["lag1_sobre_media_7"] = (lag1 > f["rolling_mean_7"]).astype(int)
    f["lag1_sobre_media_30"] = (lag1 > f["rolling_mean_30"]).astype(int)
    std30 = f["rolling_std_30"].replace(0, 1).fillna(1)
    f["lag1_z_score_30"] = (lag1 - f["rolling_mean_30"]) / std30

    # ── Suma y paridad de dígitos del lag1 ───────────────────────────────
    v1 = lag1.fillna(0).astype(int)
    suma = (v1 // 1000) % 10 + (v1 // 100) % 10 + (v1 // 10) % 10 + v1 % 10
    f["lag1_suma_digitos"] = suma
    f["lag1_suma_digitos_par"] = (suma % 2 == 0).astype(int)
    f["lag1_unidades_par"] = (v1 % 10 % 2 == 0).astype(int)

    f = f.replace([np.inf, -np.inf], np.nan)[FEATURE_COLUMNS]
    if eliminar_incompletas:
        f = f.iloc[MIN_HISTORIAL:]
    return f.fillna(0)


def features_para_proximo_sorteo(df: pd.DataFrame, fecha_proxima) -> pd.DataFrame:
    """
    Vector de features para el sorteo AÚN NO JUGADO (el siguiente al último conocido).
    Devuelve un DataFrame de 1 fila. Usa solo resultados ya conocidos.
    """
    base = df[["fecha", "result"]].copy()
    nueva = pd.DataFrame({"fecha": [pd.to_datetime(fecha_proxima)], "result": [np.nan]})
    ext = pd.concat([base, nueva], ignore_index=True)
    return generar_features(ext, eliminar_incompletas=False).iloc[[-1]]
