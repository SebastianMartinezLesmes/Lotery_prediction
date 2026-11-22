# Implementation Plan — T1 → T9 (data leakage fix + evaluation)

> Rama: `master` · Python 3.13.2 · No build step  
> Regla: un commit por tarea según el orden T1→T2→T3→T4→T5→re-entrenar→T6→T7→T8→T9  
> Verificación base: `python -c "import main"` — debe importar limpio en todo momento

---

## Estado del proyecto (exploración previa)

- Los commits T7-T16/T22 del plan anterior **ya están mergeados en master** (af00148).
- `src/features/feature_engineering.py` aún tiene la versión **CON FUGA** (41 columnas, sin `.shift(1)`, sin `features_para_proximo_sorteo`).
- `src/utils/training_simple.py` ya tiene split cronológico de **2 bloques** (`split_idx = int(n*(1-test_size))`).
- `main.py` ya usa `df_loteria.loc[X_df.index]` para alineación.
- `prediction.py` aún usa `X_train_df.tail(1).values` (fuga en predicción).
- Existen 4 `.pkl` en `IA_models/` (entrenados con features contaminadas).
- `pytest` **no está instalado**; `tests/` no existe.
- `scripts/permutation_test.py` y `scripts/backtesting.py` no existen.

---

## T1 — Reemplazar generar_features con versión anti-fuga

**Qué hacer:** Reemplazar el contenido completo de `src/features/feature_engineering.py` con el bloque Python al final de `Docs/Task_To_Do.md`. Cambios clave respecto a la versión actual:
- Todos los estadísticos de ventana (rolling, racha, diff, freq, dias_desde_ultimo) se calculan sobre `r` completa y luego se desplazan 1 posición con `base = base.shift(1)` — esto garantiza que la fila i solo puede usar r[0..i-1].
- `freq_10/30/90` pasan a `freq_lag1_10/30/90` (frecuencia del número anterior, no del objetivo).
- `dias_desde_ultimo` usa -1 para "nunca visto" (antes 0).
- Nuevo parámetro `eliminar_incompletas=True` descarta las primeras 7 filas (MIN_HISTORIAL=7).
- Nueva función `features_para_proximo_sorteo(df, fecha_proxima)` para predecir el siguiente sorteo.

**Archivos:** `src/features/feature_engineering.py`

**Verificar:**
```
python -c "from src.features.feature_engineering import generar_features, features_para_proximo_sorteo, FEATURE_COLUMNS; print(len(FEATURE_COLUMNS))"
```
Resultado esperado: `41`

**Commit:**
```
git add src/features/feature_engineering.py
git commit -m "fix: T1 replace generar_features with anti-leakage version (shift-1 pattern)"
```

---

## T2 — Crear tests/test_no_leakage.py

**Qué hacer:**
1. `pip install pytest` (añadir `pytest>=7.0.0` a `requirements.txt`).
2. Crear `tests/` y `tests/__init__.py` (vacío).
3. Crear `tests/test_no_leakage.py` copiando exactamente el bloque de pruebas del final de `Docs/Task_To_Do.md` (4 funciones):
   - `test_cambiar_resultado_i_no_altera_features_hasta_i` — cambia r[i] y verifica que las filas 0..i no cambian.
   - `test_el_futuro_si_cambia` — sanity check: las filas i+1..i+10 sí cambian.
   - `test_proximo_sorteo_usa_solo_conocidos` — verifica que `result_lag_1` del vector de predicción iguala el último resultado conocido.
   - `test_columnas_y_alineacion` — verifica que `len(X) == len(df) - 7` y que `X.index[0] == 7`.

**Archivos:** `tests/__init__.py` (crear), `tests/test_no_leakage.py` (crear), `requirements.txt` (añadir pytest)

**Verificar:**
```
python -m pytest tests/ -q
```
Resultado esperado: `4 passed` sin warnings críticos.

**Commit:**
```
git add tests/ requirements.txt
git commit -m "test: T2 add anti-leakage test suite (4 tests, all passing)"
```

---

## T3 — Alinear objetivo y features por índice en entrenamiento

**Qué hacer:** En `main.py`, función `ejecutar_entrenamiento`, bloque de preparación de features (después de `X_df = generar_features(df_loteria)`):

- La línea `X_df = X_df.replace([np.inf, -np.inf], np.nan).dropna()` debe cambiar a `X_df = X_df.replace([np.inf, -np.inf], np.nan)` — eliminar el `.dropna()` porque `eliminar_incompletas=True` en la nueva `generar_features` ya garantiza que no hay filas con NaN estructurales en las primeras 7 posiciones. El `.dropna()` post-hoc desalinearía los índices.
- Verificar que la línea de alineación ya es `df_loteria = df_loteria.loc[X_df.index]` (ya mergeada) — dejarla tal cual.
- Verificar que `y_r = df_loteria["result"].values` y `y_s = df_loteria["series"].values` están DESPUÉS de la alineación — dejarlos tal cual.

**Archivos:** `main.py`

**Verificar:**
```
python -c "import main"
python main.py --entrenar --modo test --lottery "ASTRO LUNA"
```
El entrenamiento debe completar sin "ValueError: shapes mismatch" o "IndexError".

**Commit:**
```
git add main.py
git commit -m "fix: T3 remove post-hoc dropna from training pipeline (alignment by index)"
```

---

## T4 — Corregir prediction.py para predecir el siguiente sorteo

**Qué hacer:** En `src/utils/prediction.py`, función `predecir_para_loteria`, reemplazar:
```python
features = X_train_df.tail(1).values
```
con:
```python
ultima_fecha = df_loteria["fecha"].max()
fecha_proxima = ultima_fecha + pd.Timedelta(days=1)
from src.features.feature_engineering import features_para_proximo_sorteo
features = features_para_proximo_sorteo(df_loteria, fecha_proxima).values
```

La variable `X_train_df` sigue siendo necesaria para calcular `y_result` y `y_series` (para la alineación `df_loteria = df_loteria.loc[X_train_df.index]`), así que **no eliminarla** — solo reemplazar la línea de `features`.

Verificar que después del cambio, el `result_lag_1` del vector de predicción es igual al último resultado conocido en la BD. Este invariante es: `features_para_proximo_sorteo(df, fecha)["result_lag_1"].iloc[0] == df["result"].iloc[-1]` (cubierto por `test_proximo_sorteo_usa_solo_conocidos`).

**Archivos:** `src/utils/prediction.py`

**Verificar:**
```
python -c "from src.utils.prediction import predecir_para_loteria; print('ok')"
```

**Commit:**
```
git add src/utils/prediction.py
git commit -m "fix: T4 use features_para_proximo_sorteo in prediction (no contamination)"
```

---

## T5 — Invalidar modelos .pkl actuales

**Qué hacer:**

**a) Borrar los 4 .pkl contaminados:**
```
git rm IA_models/1_astro_luna_result.pkl
git rm IA_models/1_astro_luna_series.pkl
git rm IA_models/2_astro_luna_result.pkl
git rm IA_models/2_astro_luna_series.pkl
```

**b) En `src/utils/save_training.py`, función `guardar_modelo_si_mejora`:** al cargar el modelo existente en el slot (el bloque `if os.path.exists(modelo_path):`), añadir un chequeo de compatibilidad ANTES de comparar accuracies:
```python
existente = joblib.load(modelo_path)
# Chequeo de compatibilidad de features
if existente.get("feature_names") != FEATURE_COLUMNS:
    print(f"  ⚠ Modelo obsoleto ignorado (feature_names no coincide): {os.path.basename(modelo_path)}")
    acc_existente = 0
else:
    acc_existente = existente.get("accuracy", 0)
```

**c) Verificar que `python main.py --predecir`** sin modelos muestra el mensaje: `"No se encontraron modelos entrenados para 'ASTRO LUNA'"` sin lanzar excepción. Este mensaje ya existe en `prediction.py` — solo verificar que funciona con carpeta vacía.

**Archivos:** `IA_models/*.pkl` (borrar via git rm), `src/utils/save_training.py`

**Verificar:**
```
python main.py --predecir --lottery "ASTRO LUNA"
```
Debe mostrar `"No se encontraron modelos entrenados"` sin traceback.

**Commit:**
```
git add src/utils/save_training.py
git commit -m "fix: T5 delete contaminated models and add feature_names compatibility check"
```
(Los git rm de los .pkl ya los añade automáticamente al index.)

---

## Re-entrenar (verificación end-to-end)

**Qué hacer:** Ejecutar el pipeline de entrenamiento en modo test para verificar que T1-T5 funcionan de extremo a extremo:
```
python main.py --entrenar --modo test --lottery "ASTRO LUNA"
```

Verificar que:
1. Carga datos desde Neon o fallback Excel.
2. Genera features con la nueva `generar_features` (sin fuga).
3. El entrenamiento completa sin errores.
4. Se guardan nuevos `.pkl` en `IA_models/` con la nueva `feature_names` (los 41 nombres nuevos).

Si Neon no está disponible, el fallback a `data/resultados_astro.xlsx` debe funcionar.

**Archivos:** `IA_models/` (se generan nuevos .pkl)

**Verificar:**
```
python main.py --entrenar --modo test
python -c "import joblib, os; p=[f for f in os.listdir('IA_models') if f.endswith('.pkl')]; print(p)"
```

**Commit:**
```
git add IA_models/
git commit -m "chore: re-train models after T1-T5 data leakage fix"
```

---

## T6 — Split 3 bloques cronológicos en training_simple.py

**Qué hacer:** En `src/utils/training_simple.py`, función `_evaluar_individuo`:

Reemplazar el split actual de 2 bloques:
```python
n = len(X)
split_idx = int(n * (1 - test_size))
X_tr, X_te = X[:split_idx], X[split_idx:]
# ... etc
```

Con split de 3 bloques fijos (70/15/15):
```python
n = len(X)
n_test = int(n * 0.15)
n_val  = int(n * 0.15)
n_train = n - n_val - n_test

X_tr  = X[:n_train]
X_val = X[n_train:n_train + n_val]
X_te  = X[n_train + n_val:]

ym_tr,  ym_val,  ym_te  = y_miles[:n_train],    y_miles[n_train:n_train+n_val],    y_miles[n_train+n_val:]
yc_tr,  yc_val,  yc_te  = y_centenas[:n_train],  y_centenas[n_train:n_train+n_val],  y_centenas[n_train+n_val:]
yd_tr,  yd_val,  yd_te  = y_decenas[:n_train],   y_decenas[n_train:n_train+n_val],   y_decenas[n_train+n_val:]
yu_tr,  yu_val,  yu_te  = y_unidades[:n_train],  y_unidades[n_train:n_train+n_val],  y_unidades[n_train+n_val:]
ys_tr,  ys_val,  ys_te  = y_series[:n_train],    y_series[n_train:n_train+n_val],    y_series[n_train+n_val:]
```

El algoritmo genético (fitness) evalúa sobre **validación** (`_val`). Añadir al dict retornado por `_evaluar_individuo` los campos `acc_test_result` y `acc_test_series` (accuracy sobre `_te`) pero NO usarlos en el fitness.

En `entrenar_modelos_por_loteria`, al final (sección `# ── Resultado final`): repetir el mismo split 70/15/15 sobre X completo, evaluar `mejor_modelo_result` sobre `X_te` una sola vez para obtener `accuracy_test_final_result` y `accuracy_test_final_series`. Reportar estos como las métricas definitivas.

En `guardar_modelo_si_mejora` (`save_training.py`): añadir parámetros opcionales `accuracy_val=None, accuracy_test=None` y añadirlos al payload: `"accuracy_val": accuracy_val, "accuracy_test": accuracy_test`.

**Archivos:** `src/utils/training_simple.py`, `src/utils/save_training.py`

**Verificar:**
```
python -c "from src.utils.training_simple import entrenar_modelos_por_loteria"
python main.py --entrenar --modo test --lottery "ASTRO LUNA"
python -c "import joblib, os; p=[f for f in os.listdir('IA_models') if f.endswith('.pkl')][0]; d=joblib.load('IA_models/'+p); print('accuracy_val' in d, 'accuracy_test' in d)"
```
Resultado esperado: `True True`

**Commit:**
```
git add src/utils/training_simple.py src/utils/save_training.py
git commit -m "feat: T6 three-block chronological split train70/val15/test15"
```

---

## T7 — Líneas base correctas sobre bloque test

**Qué hacer:** En `src/utils/training_simple.py`, función `entrenar_modelos_por_loteria`, reemplazar el bloque de línea base actual (que usa `Counter(y_result % 10)` sobre todo el dataset) con el cálculo correcto sobre el **bloque test**:

```python
from collections import Counter

# ── Líneas base sobre bloque TEST ─────────────────────────────
# (usar los mismos cortes 70/15/15 ya calculados)
n_test = int(len(X) * 0.15)
n_val  = int(len(X) * 0.15)
n_train = len(X) - n_val - n_test

y_miles_te    = (y_result[n_train+n_val:] // 1000) % 10
y_centenas_te = (y_result[n_train+n_val:] // 100)  % 10
y_decenas_te  = (y_result[n_train+n_val:] // 10)   % 10
y_unidades_te =  y_result[n_train+n_val:] % 10
y_series_te   =  y_series[n_train+n_val:]

base_miles    = max(Counter(y_miles_te).values())    / len(y_miles_te)
base_centenas = max(Counter(y_centenas_te).values()) / len(y_centenas_te)
base_decenas  = max(Counter(y_decenas_te).values())  / len(y_decenas_te)
base_unidades = max(Counter(y_unidades_te).values()) / len(y_unidades_te)
base_series   = max(Counter(y_series_te).values())   / len(y_series_te)

if verbose:
    print(f"\n=== LÍNEAS BASE (bloque test) ===")
    print(f"  {'Target':<12} {'Modelo':>10} {'Azar':>10} {'Más_frecuente':>15}")
    print(f"  {'Miles':<12} {acc_miles_test:>10.2%} {'10.00%':>10} {base_miles:>15.2%}")
    print(f"  {'Centenas':<12} {acc_cent_test:>10.2%} {'10.00%':>10} {base_centenas:>15.2%}")
    print(f"  {'Decenas':<12} {acc_dec_test:>10.2%} {'10.00%':>10} {base_decenas:>15.2%}")
    print(f"  {'Unidades':<12} {acc_uni_test:>10.2%} {'10.00%':>10} {base_unidades:>15.2%}")
    print(f"  {'Signo':<12} {acc_series_test:>10.2%} {'8.33%':>10} {base_series:>15.2%}")
```

Donde `acc_miles_test`, `acc_cent_test`, etc. son los accuracies por dígito del mejor modelo sobre el bloque test (calculados en T6).

**Archivos:** `src/utils/training_simple.py`

**Verificar:**
```
python main.py --entrenar --modo test --lottery "ASTRO LUNA"
```
El output debe contener `=== LÍNEAS BASE (bloque test) ===` con los 5 targets.

**Commit:**
```
git add src/utils/training_simple.py
git commit -m "feat: T7 correct baseline metrics per digit and sign on test block"
```

---

## T8 — Script de prueba de permutación

**Qué hacer:** Crear `scripts/permutation_test.py` con la siguiente estructura:

```python
"""
Prueba de permutación: mide si el modelo tiene señal real sobre el azar.
Uso: python scripts/permutation_test.py --lottery "ASTRO LUNA"
"""
import argparse
import numpy as np
import pandas as pd
from collections import Counter

# Cargar datos (Neon o Excel)
# Separar mismo split 70/15/15
# Entrenar modelo real con X_tr, evaluar en X_te → acc_real por dígito y signo
# Repetir 30 veces:
#   - barajar y_result_train (np.random.default_rng().shuffle) y y_series_train
#   - re-entrenar con y barajada, evaluar en X_te
#   - registrar accuracies
# p-valor = proporción de runs donde acc_shuffled >= acc_real
# Imprimir tabla
```

CLI: `argparse` con `--lottery` (default `"ASTRO LUNA"`).

Fallback Excel: `from src.excel.read_excel import leer_excel` o directamente `pd.read_excel("data/resultados_astro.xlsx")`.

El entrenamiento dentro del script usa `TRAINING_MODE=test` (n_jobs=1, 2 iteraciones) para que las 30 repeticiones sean rápidas.

**Archivos:** `scripts/permutation_test.py`

**Verificar:**
```
python scripts/permutation_test.py --lottery "ASTRO LUNA"
```
Debe imprimir tabla con columnas `Target | Acc_Real | Mean_Shuffled | p-valor` para los 5 targets.

**Commit:**
```
git add scripts/permutation_test.py
git commit -m "feat: T8 permutation test script (30 shuffled runs, p-value per digit and sign)"
```

---

## T9 — Script de backtesting

**Qué hacer:** Crear `scripts/backtesting.py` siguiendo el algoritmo de `Docs/Task_backtesting.md`:

**Estructura:**
```
argparse:
  --lottery   (default "ASTRO LUNA")
  --ventana   (default 100)
  --reentrenar N  (re-entrenar cada N sorteos nuevos, opcional)
  --solo-evaluar  (flag: cargar modelos existentes sin re-entrenar)

Flujo:
  1. Cargar datos desde Neon o fallback Excel
  2. df_train_base = df.iloc[:-ventana]; df_test = df.iloc[-ventana:]
  3. Entrenamiento inicial (--modo test) con nombre_slot = lottery + "_backtest"
  4. Loop for i in range(len(df_test)):
       df_acum = concat(df_train_base, df_test.iloc[:i]).reset_index(drop=True)
       X_df = generar_features(df_acum)
       features = X_df.tail(1).values   # ← en backtesting evaluamos sorteo ya conocido
       top3_numeros = modelo_result.top3_numeros(features)
       top3_signos  = (predict_proba del modelo_series)
       registrar en resultados[]
       si --reentrenar y i % N == 0 and i > 0: re-entrenar
  5. Calcular métricas: acierto_exacto, real_en_top3, acierto_serie, acc por dígito,
     mejora_vs_azar, mejora_vs_lag1. Intervalo de confianza: ±1.96*sqrt(p*(1-p)/N)
  6. df_res.to_csv("data/backtesting_results.csv", index=False)
  7. Imprimir resumen con la tabla de Docs/Task_backtesting.md
```

**Nota sobre buscar_mejor_modelo:** importar directamente desde `src/utils/prediction.py`:
```python
from src.utils.prediction import buscar_mejor_modelo
```
Para cargar los modelos con sufijo `_backtest` después del entrenamiento inicial.

**Archivos:** `scripts/backtesting.py`, `data/backtesting_results.csv` (generado al ejecutar)

**Verificar:**
```
python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100
python -c "import pandas as pd; df=pd.read_csv('data/backtesting_results.csv'); print(df.columns.tolist()); print(len(df))"
```
Debe mostrar las columnas definidas en `Docs/Task_backtesting.md` y 100 filas.

**Commit:**
```
git add scripts/backtesting.py data/backtesting_results.csv
git commit -m "feat: T9 backtesting script with expanding window sorteo-by-sorteo evaluation"
```

---

## Orden de dependencias

```
T1 (feature_engineering.py)
  └─→ T2 (tests — verifica T1)
  └─→ T3 (main.py — elimina dropna post-hoc)
  └─→ T4 (prediction.py — usa features_para_proximo_sorteo)
         └─→ T5 (borrar .pkl, chequeo en save_training.py)
                └─→ Re-entrenar (verifica T1-T5 end-to-end)
                       └─→ T6 (training_simple.py: split 3 bloques)
                              └─→ T7 (baselines sobre bloque test)
                                     └─→ T8 (permutation_test.py)
                                     └─→ T9 (backtesting.py)
```

T8 y T9 son independientes entre sí y pueden implementarse en cualquier orden.

---

## Restricciones que no cambiar

- No modificar el algoritmo RandomForest/genético (`_ModeloCompuesto`, `_cruzar`, `_mutar`, `_nueva_generacion`).
- No borrar datos de Neon.
- Siempre `--modo test` en verificaciones.
- Scripts nuevos (T8, T9) deben funcionar sin Neon: usar `data/resultados_astro.xlsx` como fallback.
- Sin archivos de log — solo consola.

---

## Criterio global de aceptación

1. `python -m pytest tests/ -q` → 4 passed.
2. `python main.py --entrenar --modo test` → completa, muestra `=== LÍNEAS BASE (bloque test) ===`.
3. Los `.pkl` guardados tienen claves `accuracy_val` y `accuracy_test`.
4. `python scripts/permutation_test.py --lottery "ASTRO LUNA"` → tabla con p-valores.
5. `python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100` → `data/backtesting_results.csv` con 100 filas.
