import numpy as np, pandas as pd
from src.features.feature_engineering import generar_features, features_para_proximo_sorteo, FEATURE_COLUMNS

def _datos(n=300, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"fecha": pd.date_range("2023-10-01", periods=n),
                         "result": rng.integers(0, 10000, n)})

def test_cambiar_resultado_i_no_altera_features_hasta_i():
    df = _datos()
    base = generar_features(df, eliminar_incompletas=False)
    for i in (10, 100, 250):
        df2 = df.copy()
        df2.loc[i, "result"] = (df2.loc[i, "result"] + 1234) % 10000
        alt = generar_features(df2, eliminar_incompletas=False)
        pd.testing.assert_frame_equal(base.iloc[:i + 1], alt.iloc[:i + 1])

def test_el_futuro_si_cambia():  # sanity: la prueba realmente detecta cambios
    df = _datos(); df2 = df.copy(); df2.loc[100, "result"] = (df2.loc[100, "result"] + 1) % 10000
    a = generar_features(df, False); b = generar_features(df2, False)
    assert not a.iloc[101:110].equals(b.iloc[101:110])

def test_proximo_sorteo_usa_solo_conocidos():
    df = _datos()
    x = features_para_proximo_sorteo(df, "2099-01-01")
    assert list(x.columns) == FEATURE_COLUMNS and len(x) == 1
    assert x["result_lag_1"].iloc[0] == df["result"].iloc[-1]

def test_columnas_y_alineacion():
    df = _datos(); X = generar_features(df)
    assert list(X.columns) == FEATURE_COLUMNS and len(X) == len(df) - 7
    assert X.index[0] == 7
