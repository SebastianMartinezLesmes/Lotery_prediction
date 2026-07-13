import pandas as pd

FEATURE_COLUMNS = [
    "dia", "mes", "anio", "dia_semana",
    "dia_mes", "semana_anio", "trimestre",
    "es_fin_semana", "es_inicio_mes", "es_fin_mes",
    "result_lag_1", "result_lag_2", "result_lag_3",
    "result_rolling_mean_7", "result_rolling_std_7",
    "result_rolling_mean_30", "result_rolling_std_30",
    "tendencia_7",
    "result_freq_mean", "result_freq_std",
    # Paso 2: frecuencia histórica
    "freq_result_30", "freq_result_90", "dias_desde_ultimo"
]


def generar_features(df):
    df = df.sort_values("fecha").copy()

    # Temporales básicas
    df["dia"]        = df["fecha"].dt.day
    df["mes"]        = df["fecha"].dt.month
    df["anio"]       = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    df["dia_mes"]    = df["fecha"].dt.day
    df["semana_anio"]= df["fecha"].dt.isocalendar().week
    df["trimestre"]  = df["fecha"].dt.quarter
    df["es_fin_semana"]  = (df["dia_semana"] >= 5).astype(int)
    df["es_inicio_mes"]  = (df["dia"] <= 7).astype(int)
    df["es_fin_mes"]     = (df["dia"] >= 23).astype(int)

    # Lag
    df["result_lag_1"] = df["result"].shift(1)
    df["result_lag_2"] = df["result"].shift(2)
    df["result_lag_3"] = df["result"].shift(3)

    # Rolling
    df["result_rolling_mean_7"]  = df["result"].rolling(7,  min_periods=1).mean()
    df["result_rolling_std_7"]   = df["result"].rolling(7,  min_periods=1).std()
    df["result_rolling_mean_30"] = df["result"].rolling(30, min_periods=1).mean()
    df["result_rolling_std_30"]  = df["result"].rolling(30, min_periods=1).std()

    # Tendencia
    df["tendencia_7"] = (
        df["result"].rolling(7, min_periods=1)
        .apply(lambda x: 1 if len(x) > 1 and x.iloc[-1] > x.iloc[0] else 0)
    )

    # Frecuencia (rolling mean/std — alias para compatibilidad)
    df["result_freq_mean"] = df["result"].rolling(30, min_periods=1).mean()
    df["result_freq_std"]  = df["result"].rolling(30, min_periods=1).std()

    # ── PASO 2: Frecuencia histórica del número ──────────────────────────
    # Cuántas veces apareció este número en los últimos 30 y 90 sorteos
    def freq_en_ventana(series, ventana):
        resultado = []
        vals = series.values
        for i in range(len(vals)):
            inicio = max(0, i - ventana)
            ventana_vals = vals[inicio:i]
            resultado.append((ventana_vals == vals[i]).sum())
        return resultado

    df["freq_result_30"] = freq_en_ventana(df["result"], 30)
    df["freq_result_90"] = freq_en_ventana(df["result"], 90)

    # Días desde la última aparición del mismo número
    last_seen = {}
    dias_desde = []
    for i, row in df.iterrows():
        n = row["result"]
        if n in last_seen:
            dias_desde.append((row["fecha"] - last_seen[n]).days)
        else:
            dias_desde.append(0)
        last_seen[n] = row["fecha"]
    df["dias_desde_ultimo"] = dias_desde

    df = df.fillna(0)

    return df[FEATURE_COLUMNS]

