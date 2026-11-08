# Tareas para Kiro — corregir fuga de datos y validar el modelo

> Fecha: 2026-10-04 · Repositorio: `Lotery_prediction` · Rama: `master`
> Archivos adjuntos a este documento (en la carpeta `kiro_fix/`):
> - `feature_engineering_corregido.py` → reemplaza `src/features/feature_engineering.py`
> - `test_no_leakage.py` → copiar a `tests/test_no_leakage.py`

## Contexto (leer primero)

`generar_features` tiene **fuga de datos**: la fila *i* (el sorteo que se quiere predecir) incluye información del propio resultado `r[i]`.

| Feature con fuga | Motivo |
|---|---|
| `diff_1`, `diff_abs_1`, `signo_diff_1` | `r.diff(1)` = `r[i] - r[i-1]`; junto con `result_lag_1` revela `r[i]` exacto |
| `racha` | Incluye la diferencia del sorteo *i* |
| `rolling_mean/std/max/min/range_*` | La ventana incluye `r[i]` |
| `tendencia_7`, `tendencia_30` | Usan `x.iloc[-1]` = `r[i]` |
| `freq_10/30/90` | Cuenta cuántas veces apareció el número `r[i]` |
| `dias_desde_ultimo` | Días desde la última aparición de `r[i]` |

Consecuencias: el accuracy de ~25% y la confianza de 18,33% no son confiables; la "reversión a la media" (autocorr de `diff` = -0.465) es un artefacto matemático (para cualquier serie independiente da ≈ -0.5); y `prediction.py` usa la última fila, que ya contiene el último sorteo conocido en lugar de predecir el siguiente.

**Regla nueva:** la fila *i* solo puede usar `r[0..i-1]`.

**Reglas de trabajo:** un commit por tarea. No cambiar el algoritmo (RandomForest/genético) en este plan. No borrar datos de Neon.

---

## Fase 1 — Corregir la fuga

### T1. Reemplazar `generar_features`
- **Archivo:** `src/features/feature_engineering.py`
- **Hacer:** sustituir su contenido por `feature_engineering_corregido.py`. Cambios clave:
  - Los estadísticos de ventana se calculan sobre `r` y luego se aplica `.shift(1)`.
  - `freq_10/30/90` pasan a llamarse `freq_lag1_10/30/90` (frecuencia del **último número conocido**, no del objetivo).
  - `dias_desde_ultimo` usa `-1` para "nunca visto" (antes 0, ambiguo).
  - Nuevo parámetro `eliminar_incompletas=True`: descarta las primeras 7 filas en lugar de rellenar con ceros. El índice del resultado conserva la posición del sorteo.
  - Nueva función `features_para_proximo_sorteo(df, fecha_proxima)`.
- **Listo cuando:** `FEATURE_COLUMNS` sigue teniendo 41 columnas y el módulo importa sin errores.

### T2. Añadir la prueba anti-fuga
- **Archivo:** `tests/test_no_leakage.py` (crear carpeta `tests/` si no existe).
- **Hacer:** copiar el archivo adjunto y ejecutar `python -m pytest tests/ -q` (añadir `pytest` a `requirements-dev.txt` si no está).
- **Listo cuando:** las 4 pruebas pasan. La prueba principal cambia `result[i]` y exige que las features de las filas `0..i` no cambien.
- **Nota:** esta prueba debe **fallar** con el código anterior. Si Kiro quiere confirmarlo, que la ejecute antes de T1.

### T3. Alinear objetivo y features por índice
- **Archivo:** `main.py` (`ejecutar_entrenamiento`).
- **Problema:** se usa `df_loteria.tail(len(X_df))`.
- **Hacer:** ordenar `df_loteria` por fecha con `reset_index(drop=True)`, generar `X_df = generar_features(df_loteria)` y obtener los objetivos con `df_loteria.loc[X_df.index, ["result", "series"]]`. Eliminar el `dropna()` posterior (ya no hace falta).
- **Listo cuando:** `len(X) == len(y)` y para la primera fila `X.index[0] == 7` corresponde al sorteo 8.º del historial.

### T4. Predecir el siguiente sorteo, no uno ya conocido
- **Archivo:** `src/utils/prediction.py`.
- **Hacer:** en lugar de tomar la última fila de `generar_features(df)`, usar `features_para_proximo_sorteo(df, fecha_proxima)`. La fecha próxima es el siguiente día de sorteo; si no se conoce el calendario, usar `ultima_fecha + 1 día`.
- **Listo cuando:** el `result_lag_1` de la fila usada es igual al último resultado de la base de datos.

### T5. Invalidar los modelos actuales
- **Carpeta:** `IA_models/`.
- **Hacer:** borrar los `.pkl` existentes (fueron entrenados con features contaminadas) y añadir en `save_training.py` un chequeo: al cargar un modelo, si `feature_names` del metadata no coincide con `FEATURE_COLUMNS`, ignorarlo con un aviso.
- **Listo cuando:** `python main.py --predecir` sin modelos muestra un mensaje claro de "no hay modelo, ejecuta --entrenar" en lugar de fallar.

---

## Fase 2 — Medir de forma honesta

### T6. Tres bloques cronológicos
- **Archivo:** `src/utils/training_simple.py`.
- **Problema:** el algoritmo genético elige al mejor individuo por accuracy en el mismo bloque que luego se reporta.
- **Hacer:**
  - Train: primeros 70% · Validación: siguiente 15% · Test: último 15%, por orden cronológico.
  - El algoritmo genético y la regla de slots usan **solo validación**.
  - El test se calcula **una sola vez** al final y es la única cifra que se guarda como `accuracy_test` y se reporta.
- **Listo cuando:** el metadata del `.pkl` incluye `accuracy_val` y `accuracy_test` por separado.

### T7. Líneas base correctas
- **Archivo:** `training_simple.py` (reemplaza el bloque "Línea base").
- **Hacer:** calcular y mostrar, sobre el bloque de test:
  - Dígitos: azar = 10% y frecuencia de la clase más frecuente **por cada posición** (miles, centenas, decenas, unidades), no solo unidades.
  - Signo: azar = 8,3% y clase más frecuente.
  - Reportar el "accuracy por dígito" con ese nombre; no compararlo con 0,11%.
- **Listo cuando:** el log muestra "modelo vs. azar vs. más frecuente" para los 4 dígitos y el signo.

### T8. Prueba de permutación
- **Crear:** `scripts/permutation_test.py`.
- **Hacer:** entrenar con perfil `test`, medir accuracy en el bloque de test; barajar `y` del bloque de train 30 veces y repetir. Imprimir el p-valor (proporción de corridas barajadas con accuracy ≥ al real) por dígito y por signo.
- **Listo cuando:** el script imprime una tabla con accuracy real, media barajada y p-valor. Un p-valor > 0,05 se interpreta como "sin señal detectable".

### T9. Backtesting sorteo a sorteo
- **Crear:** `scripts/backtesting.py` según `Docs/Task_backtesting.md`.
- **Hacer:** ventana expansiva: para cada uno de los últimos N sorteos (N=100), entrenar con lo anterior (perfil `test`), predecir ese sorteo y registrar acierto por dígito, por signo y top-3. Imprimir resumen y compararlo con el azar.
- **Listo cuando:** el script termina y reporta las métricas con su intervalo de confianza aproximado (±1,96·√(p(1-p)/N)).

### T10. Regla de decisión en el pipeline
- **Archivo:** `src/utils/prediction.py` / `main.py`.
- **Hacer:** si el último `accuracy_test` guardado del modelo no supera al azar de forma significativa (criterio de T8), la predicción debe imprimir: "Sin señal detectable sobre el azar" y mostrar las probabilidades solo como referencia, sin presentarlas como acierto esperado.
- **Listo cuando:** el output de `--predecir` incluye esa advertencia cuando corresponde.

---

## Fase 3 — Documentación y ajustes menores

### T11. Corregir afirmaciones no sustentadas
- **Archivos:** `Docs/MEJORAS_IA.md`, `Docs/MEJORAS_ML.md`, `Docs/FEATURES.md`, docstring de `feature_engineering.py`.
- **Hacer:**
  - Eliminar la afirmación de "reversión a la media" y la tabla de autocorrelaciones como "señal detectada".
  - Eliminar "existen patrones explotables" y el "límite práctico 30–35%".
  - Eliminar las estimaciones de "+2–5% accuracy" por XGBoost y "+1–2%" por lag4/lag5 (no están medidas).
  - Documentar la fuga que se corrigió y la fecha.
  - Reemplazar las métricas actuales por las nuevas (T6–T9) cuando existan.

### T12. Quitar `total == 0` como criterio de fallo
- **Archivo:** `scripts/sync_check.py`.
- **Problema:** si la base ya está al día y el sitio no publicó nada, el job falla sin motivo.
- **Hacer:** fallar solo por excepción o por fecha vencida (`MAX(fecha) < hoy - 3 días`). Actualizar `Docs/SCHEDULER.md`.
- **Listo cuando:** una ejecución con base al día termina en verde.

### T13. Sincronización diaria
- **Archivo:** `.github/workflows/sync_neon.yml`.
- **Hacer:** cambiar el cron a `0 12 * * *` (la sincronización es incremental e idempotente). Actualizar `Docs/SCHEDULER.md` y `Docs/ARCHITECTURE.md`.

### T14. Alertas con umbrales realistas
- **Archivo:** `src/core/config.py` / `.env.example`.
- **Hacer:** ajustar `ALERT_ACCURACY_WARNING` y `ALERT_ACCURACY_CRITICAL` a valores relativos al azar (por ejemplo, alertar si el accuracy de test no supera el azar), de modo que dejen de dispararse siempre.

### T15. Aviso en el README
- **Archivo:** `README.md`.
- **Hacer:** añadir una sección breve indicando que los sorteos son eventos aleatorios, que el proyecto es experimental/educativo, y mostrar las métricas validadas de T6–T9 (no las anteriores).

---

## Orden y criterio global de aceptación

Orden: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11–T15.

El plan está terminado cuando:
1. `pytest tests/` pasa, incluida la prueba anti-fuga.
2. El entrenamiento reporta accuracy de **validación** y de **test** separados, con línea base correcta.
3. Existen resultados de la prueba de permutación y del backtesting.
4. La documentación ya no afirma señal que no esté medida.

**Resultado esperable (no es un error):** tras corregir la fuga, el accuracy por dígito probablemente baje a ~10% y el del signo a ~8%. Eso significa que ahora la medición es correcta. Si en cambio queda una mejora pequeña, constante en el test, en el backtesting y con p-valor bajo, entonces vale la pena seguir investigando.

## Fuera de alcance

- Cambiar el algoritmo de entrenamiento, integrar XGBoost/LightGBM o añadir lag4/lag5 (esperar a que T8–T9 muestren si hay señal).
- Cambios en la base de datos o el scraper.




----------------------------------------
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

    ------------------------------------------------

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