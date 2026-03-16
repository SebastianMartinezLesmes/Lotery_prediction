import pandas as pd

FEATURE_COLUMNS = [
    "dia", "mes", "anio", "dia_semana",
    "dia_mes", "semana_anio", "trimestre",
    "es_fin_semana", "es_inicio_mes", "es_fin_mes",
    "result_lag_1", "result_lag_2", "result_lag_3",
    "result_rolling_mean_7", "result_rolling_std_7",
    "result_rolling_mean_30", "result_rolling_std_30",
    "tendencia_7",
    "result_freq_mean", "result_freq_std"
]


def generar_features(df):
    
    df = df.sort_values("fecha").copy()

    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday

    df["dia_mes"] = df["fecha"].dt.day
    df["semana_anio"] = df["fecha"].dt.isocalendar().week
    df["trimestre"] = df["fecha"].dt.quarter
    df["es_fin_semana"] = (df["dia_semana"] >= 5).astype(int)
    df["es_inicio_mes"] = (df["dia"] <= 7).astype(int)
    df["es_fin_mes"] = (df["dia"] >= 23).astype(int)

    df["result_lag_1"] = df["result"].shift(1)
    df["result_lag_2"] = df["result"].shift(2)
    df["result_lag_3"] = df["result"].shift(3)

    df["result_rolling_mean_7"] = df["result"].rolling(7, min_periods=1).mean()
    df["result_rolling_std_7"] = df["result"].rolling(7, min_periods=1).std()

    df["result_rolling_mean_30"] = df["result"].rolling(30, min_periods=1).mean()
    df["result_rolling_std_30"] = df["result"].rolling(30, min_periods=1).std()

    df["tendencia_7"] = (
        df["result"].rolling(7, min_periods=1)
        .apply(lambda x: 1 if len(x) > 1 and x.iloc[-1] > x.iloc[0] else 0)
    )

    df["result_freq_mean"] = df["result"].rolling(30, min_periods=1).mean()
    df["result_freq_std"] = df["result"].rolling(30, min_periods=1).std()

    df = df.fillna(0)

    return df[FEATURE_COLUMNS]