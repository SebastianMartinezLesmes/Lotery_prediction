# Task: Backtesting del modelo de predicción

Documento de planificación para implementar la evaluación real del modelo
sobre datos históricos, simulando condiciones de producción.

---

## Qué es el backtesting y por qué lo necesitamos

El entrenamiento actual evalúa el modelo con un split aleatorio 80/20 del
historial completo. Eso responde: *"¿qué tan bien memorizó el pasado?"*

El backtesting temporal responde la pregunta correcta: *"¿qué tan bien hubiera
predicho el modelo si lo hubiéramos usado en producción, sorteo por sorteo?"*

La diferencia es crítica. Un split aleatorio puede usar datos del futuro para
entrenar (ej. el sorteo del 1 de mayo en el train, pero el del 15 de abril en
el test), lo que sobreestima la capacidad real del modelo.

---

## Líneas de referencia actuales (medidas sobre ASTRO LUNA, 996 registros)

Antes de implementar, estos son los números contra los que hay que comparar:

| Estrategia | Acierto número exacto | Acierto dígito (promedio) |
|---|---|---|
| Azar puro | 0.11% (1 / 909 clases) | 10.00% |
| Repetir número anterior | 5.02% | ~14.8% |
| Modelo actual (split aleatorio) | ~25.25% | — |
| **Modelo con backtesting real** | **por medir** | **por medir** |

El objetivo del backtesting es medir la columna "por medir" con honestidad.

---

## Plan de implementación

### Archivo a crear

```
scripts/backtesting.py
```

### Datos de entrada

- `data/resultados_astro.xlsx` — historial local (fallback si Neon no está disponible)
- O bien: datos cargados desde Neon vía `LotteriaRepository.get_all_results()`
- Columnas requeridas: `fecha`, `lottery`, `result`, `series`
- Ordenado por `fecha` ascendente (más antiguo primero)

### Módulos del proyecto que se reutilizan

```python
from src.features.feature_engineering import generar_features, FEATURE_COLUMNS
from src.utils.training_simple import entrenar_modelos_por_loteria, _ModeloCompuesto
from src.core.config import settings
```

No se crea lógica nueva de entrenamiento — se reutiliza exactamente la misma
que usa `main.py --entrenar`, para que el backtesting sea representativo.

---

## Algoritmo paso a paso

### Parámetro clave: `ventana_test`

Cuántos sorteos del final del historial se reservan para evaluar.
El modelo **nunca ve esos datos durante el entrenamiento**.

```
ventana_test = 100   # evaluar sobre los últimos 100 sorteos

Historial completo (996 sorteos):
[========== train inicial (896) ==========][===== test (100) =====]
                                             ↑ nunca visto por el modelo
```

### Paso 1 — Separar train inicial y ventana de test

```python
df = cargar_datos(loteria)           # todos los registros ordenados por fecha
df_train_base = df.iloc[:-ventana_test]   # 896 sorteos para entrenar
df_test       = df.iloc[-ventana_test:]   # 100 sorteos para evaluar
```

### Paso 2 — Entrenamiento inicial

Entrenar el modelo con `df_train_base` usando el mismo pipeline que producción:

```python
os.environ["TRAINING_MODE"] = "prod"    # o "test" para backtest rápido

X_df = generar_features(df_train_base)
X    = X_df.values
y_r  = df_train_base.tail(len(X_df))["result"].values
y_s  = df_train_base.tail(len(X_df))["series"].values

entrenar_modelos_por_loteria(X, y_r, y_s, loteria + "_backtest")
```

### Paso 3 — Evaluación sorteo por sorteo (ventana deslizante)

Para cada sorteo `i` en `df_test`:

```
sorteo i=0:  train=[0..895]  →  predice sorteo 896  →  compara con real
sorteo i=1:  train=[0..896]  →  predice sorteo 897  →  compara con real
...
sorteo i=99: train=[0..994]  →  predice sorteo 995  →  compara con real
```

En cada paso:
1. Generar features sobre el histórico acumulado hasta `i-1`
2. Tomar la última fila como features de predicción
3. Predecir número (top-3) y signo (top-3)
4. Comparar con el resultado real del sorteo `i`
5. Registrar métricas

```python
resultados = []

for i in range(len(df_test)):
    # Historial acumulado hasta este punto (sin incluir el sorteo i)
    df_acumulado = pd.concat([df_train_base, df_test.iloc[:i]]).reset_index(drop=True)
    df_acumulado["fecha"] = pd.to_datetime(df_acumulado["fecha"])

    # Generar features
    X_df = generar_features(df_acumulado)
    features = X_df.tail(1).values       # última fila = estado actual

    # Predecir
    top3_numeros = modelo_result.top3_numeros(features)
    top3_signos  = obtener_top3_signos(modelo_series, features)

    # Resultado real
    real_result = df_test.iloc[i]["result"]
    real_series = df_test.iloc[i]["series"]

    # Registrar
    resultados.append({
        "fecha":          df_test.iloc[i]["fecha"],
        "real_result":    real_result,
        "pred_top1":      top3_numeros[0][0],
        "pred_top3":      [n for n, _ in top3_numeros],
        "real_en_top3":   real_result in [n for n, _ in top3_numeros],
        "real_series":    real_series,
        "pred_series":    top3_signos[0][0],
        "series_ok":      real_series == top3_signos[0][0],
        # Aciertos por dígito
        "miles_ok":       (real_result//1000)%10 == (top3_numeros[0][0]//1000)%10,
        "centenas_ok":    (real_result//100)%10  == (top3_numeros[0][0]//100)%10,
        "decenas_ok":     (real_result//10)%10   == (top3_numeros[0][0]//10)%10,
        "unidades_ok":    real_result%10         == top3_numeros[0][0]%10,
    })
```

### Paso 4 — Calcular métricas finales

```python
df_res = pd.DataFrame(resultados)

print("=== BACKTESTING RESULTS ===")
print(f"Sorteos evaluados    : {len(df_res)}")
print(f"Acierto exacto (top1): {df_res['pred_top1'].eq(df_res['real_result']).mean():.2%}")
print(f"Real en top-3        : {df_res['real_en_top3'].mean():.2%}")
print(f"Acierto signo        : {df_res['series_ok'].mean():.2%}")
print()
print("Acierto por dígito:")
print(f"  Miles    : {df_res['miles_ok'].mean():.2%}")
print(f"  Centenas : {df_res['centenas_ok'].mean():.2%}")
print(f"  Decenas  : {df_res['decenas_ok'].mean():.2%}")
print(f"  Unidades : {df_res['unidades_ok'].mean():.2%}")
```

### Paso 5 — Guardar resultados

```python
df_res.to_csv("data/backtesting_results.csv", index=False)
```

---

## Variante: Re-entrenamiento periódico

En producción el modelo se re-entrena con datos nuevos cada cierto tiempo.
Para simular eso en el backtesting:

```python
REENTRENAR_CADA = 30   # re-entrenar cada 30 sorteos nuevos

for i in range(len(df_test)):
    if i % REENTRENAR_CADA == 0 and i > 0:
        # Re-entrenar con todos los datos acumulados hasta aquí
        df_acumulado = pd.concat([df_train_base, df_test.iloc[:i]])
        X_df = generar_features(df_acumulado)
        ...
        entrenar_modelos_por_loteria(X, y_r, y_s, loteria + "_backtest")
        # Recargar modelo
        modelo_result, modelo_series = cargar_mejores_modelos(loteria + "_backtest")
```

Esto responde: *"¿mejora el modelo si se re-entrena a medida que llegan datos nuevos?"*

---

## CLI propuesto

```bash
# Backtest rápido (modo test, sin re-entrenamiento)
python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100

# Backtest completo (modo prod, con re-entrenamiento cada 30 sorteos)
python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100 --reentrenar 30 --modo prod

# Solo evaluar con modelo ya entrenado (sin re-entrenar)
python scripts/backtesting.py --lottery "ASTRO LUNA" --ventana 100 --solo-evaluar
```

---

## Métricas que producirá el script

| Métrica | Descripción | Por qué importa |
|---|---|---|
| `acierto_exacto` | % sorteos donde top1 == real | Medida más estricta |
| `real_en_top3` | % sorteos donde real está en las 3 predicciones | Más útil en práctica |
| `acierto_serie` | % sorteos donde el signo predicho es correcto | Independiente del número |
| `acc_miles` | % dígito de miles correcto | Ver qué posición predice mejor |
| `acc_centenas` | % dígito de centenas correcto | Idem |
| `acc_decenas` | % dígito de decenas correcto | Idem |
| `acc_unidades` | % dígito de unidades correcto | Idem |
| `mejora_vs_azar` | acierto_exacto / 0.0011 | Cuántas veces mejor que el azar |
| `mejora_vs_lag1` | acierto_exacto / 0.0502 | Cuántas veces mejor que repetir anterior |

---

## Criterio de éxito

El modelo se considera útil si:

- `real_en_top3` > 10% — el número real aparece en las 3 predicciones más
  de lo que aparecería por azar (azar top3 ≈ 0.33%)
- `acierto_serie` > 15% — supera el azar de signo (8.3%)
- `acc_unidades` > 20% — al menos el doble del azar por dígito (10%)

---

## Restricciones importantes

- El modelo de backtesting se guarda en slots separados
  (`loteria + "_backtest"`) para no sobreescribir los modelos de producción
- Los datos de test **nunca se tocan durante el entrenamiento** de cada paso
- El script debe poder ejecutarse sin conexión a Neon (usando Excel como fallback)
- El tiempo estimado para backtest completo con `ventana=100` y re-entrenamiento
  cada 30 sorteos es: 3-4 entrenamientos × 5 min = ~20 minutos

---

## Archivos que se crean al ejecutar

```
data/
  backtesting_results.csv     ← tabla completa sorteo por sorteo

IA_models/
  1_astro_luna_backtest_result.pkl   ← modelos del backtesting (no afectan producción)
  1_astro_luna_backtest_series.pkl
```

---

## Dependencias

No requiere librerías nuevas. Todo usa lo que ya está en `requirements.txt`:

```
pandas
numpy
scikit-learn
joblib
openpyxl
```
