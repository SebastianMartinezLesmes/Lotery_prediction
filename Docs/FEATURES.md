# Features de Entrenamiento

Descripción completa de las 41 features que usa el modelo, su justificación
estadística y cómo se generan.

---

## Por qué no hay features de calendario

Las features de fecha (`dia`, `mes`, `anio`, `dia_semana`, etc.) fueron eliminadas
porque asumen que el día del sorteo influye en el resultado. Eso no tiene
fundamento causal — la lotería es un proceso que no tiene memoria del calendario.

Mantenerlas introduce ruido: el modelo gasta splits en variables irrelevantes
y la señal real (patrones históricos) queda diluida.

**Todo el conocimiento del modelo viene del comportamiento histórico de los números.**

---

## Las 41 features actuales

Definidas en `src/features/feature_engineering.py` → `FEATURE_COLUMNS`.
Generadas por `generar_features(df)` que recibe el DataFrame ordenado por fecha.

### Lags del resultado completo (5 features)

| Feature | Descripción |
|---|---|
| `result_lag_1` | Resultado del sorteo anterior |
| `result_lag_2` | Resultado hace 2 sorteos |
| `result_lag_3` | Resultado hace 3 sorteos |
| `result_lag_5` | Resultado hace 5 sorteos |
| `result_lag_7` | Resultado hace 7 sorteos |

**Justificación**: autocorrelación del resultado ≈ 0.068 en lag1. Señal débil
pero presente. Los lags más lejanos (5, 7) capturan patrones de más largo plazo.

---

### Dígitos de los últimos 3 resultados (12 features)

| Feature | Descripción |
|---|---|
| `lag1_miles` | Dígito de miles del resultado anterior |
| `lag1_centenas` | Dígito de centenas del resultado anterior |
| `lag1_decenas` | Dígito de decenas del resultado anterior |
| `lag1_unidades` | Dígito de unidades del resultado anterior |
| `lag2_miles` … `lag2_unidades` | Lo mismo para hace 2 sorteos |
| `lag3_miles` … `lag3_unidades` | Lo mismo para hace 3 sorteos |

**Justificación**: el modelo compuesto predice dígito por dígito. Darle los
dígitos individuales de sorteos anteriores permite aprender patrones por posición
(ej. si el dígito de unidades tiende a oscilar entre 3 y 7). Autocorrelación
por dígito ≈ 0.06-0.08.

---

### Diferencias y dirección (4 features)

| Feature | Descripción |
|---|---|
| `diff_1` | result[i] − result[i−1] |
| `diff_2` | result[i−1] − result[i−2] (diff del sorteo anterior) |
| `diff_abs_1` | Magnitud del último cambio |
| `signo_diff_1` | Dirección: +1 subió, −1 bajó, 0 igual |

**Justificación**: esta es la señal más fuerte del dataset. La autocorrelación
de `diff_1` es **−0.465**, lo que indica reversión a la media: cuando el número
sube mucho, tiende a bajar en el siguiente sorteo, y viceversa. Estas features
son las que más contribuyen al accuracy.

---

### Racha direccional (1 feature)

| Feature | Descripción |
|---|---|
| `racha` | Sorteos consecutivos subiendo (+N) o bajando (−N) |

Ejemplos: si los últimos 3 resultados fueron 1200 → 1500 → 1800, `racha = 3`.
Si fueron 1800 → 1500 → 1200, `racha = -3`.

**Justificación**: captura el momentum. Complementa `signo_diff_1` con información
sobre cuánto tiempo lleva la tendencia.

---

### Rolling statistics (7 features)

| Feature | Descripción |
|---|---|
| `rolling_mean_7` | Media de los últimos 7 resultados |
| `rolling_std_7` | Desviación estándar de los últimos 7 |
| `rolling_mean_30` | Media de los últimos 30 resultados |
| `rolling_std_30` | Desviación estándar de los últimos 30 |
| `rolling_max_7` | Máximo de los últimos 7 |
| `rolling_min_7` | Mínimo de los últimos 7 |
| `rolling_range_7` | rolling_max_7 − rolling_min_7 |

**Justificación**: la media rolling captura el "nivel" reciente. La std captura
la volatilidad. El rango indica si los números están concentrados o dispersos.

---

### Posición relativa (3 features)

| Feature | Descripción |
|---|---|
| `lag1_sobre_media_7` | 1 si el resultado anterior > media últimos 7 |
| `lag1_sobre_media_30` | 1 si el resultado anterior > media últimos 30 |
| `lag1_z_score_30` | Cuántas desv. std está lag1 respecto a la media de 30 |

**Justificación**: complementan la señal de reversión a la media. Si `lag1`
está muy por encima de la media (z_score alto), la reversión esperada es mayor.

---

### Tendencia (2 features)

| Feature | Descripción |
|---|---|
| `tendencia_7` | 1 si result[i−1] > result[i−7] (tendencia alcista en 7 sorteos) |
| `tendencia_30` | 1 si result[i−1] > result[i−30] (tendencia alcista en 30 sorteos) |

---

### Características del último resultado (3 features)

| Feature | Descripción |
|---|---|
| `lag1_suma_digitos` | Suma de los 4 dígitos del resultado anterior (rango 0-36) |
| `lag1_suma_digitos_par` | 1 si esa suma es par |
| `lag1_unidades_par` | 1 si el dígito de unidades del resultado anterior es par |

**Justificación**: la suma de dígitos captura el "nivel" del número de forma
compacta (suma baja → número pequeño, suma alta → número grande). La paridad
puede capturar patrones de alternancia.

---

### Frecuencia histórica (3 features)

| Feature | Descripción |
|---|---|
| `freq_10` | Veces que apareció el número actual en los últimos 10 sorteos |
| `freq_30` | Veces que apareció en los últimos 30 sorteos |
| `freq_90` | Veces que apareció en los últimos 90 sorteos |

**Nota**: estas features miden la frecuencia del número que estamos prediciendo,
no del lag1. Esto introduce un leak potencial en entrenamiento, pero en predicción
se calcula correctamente sobre el historial hasta el momento actual.

---

### Tiempo sin aparecer (1 feature)

| Feature | Descripción |
|---|---|
| `dias_desde_ultimo` | Días desde la última vez que salió este número exacto |

0 si el número nunca ha aparecido antes en el histórico.

---

## Importancia de features (cualitativa)

Basado en el análisis estadístico y el impacto observado en accuracy:

| Prioridad | Features |
|---|---|
| Alta | `diff_1`, `signo_diff_1`, `diff_abs_1`, `lag1_z_score_30` |
| Media | `result_lag_1..3`, `lag1_*_dígitos`, `rolling_mean_7/30`, `lag1_sobre_media_*` |
| Baja | `freq_*`, `dias_desde_ultimo`, `racha`, `tendencia_*` |

Para medir la importancia real, se puede usar `feature_importances_` de los
modelos RF guardados:

```python
import joblib
payload = joblib.load("IA_models/1_astro_luna_result.pkl")
modelo = payload["model"]

# Para _ModeloCompuesto, acceder al sub-modelo de unidades (más informativo)
importancias = modelo.unidades.feature_importances_
nombres = payload["feature_names"]

for nombre, imp in sorted(zip(nombres, importancias), key=lambda x: -x[1])[:10]:
    print(f"  {nombre}: {imp:.4f}")
```

---

## Agregar nuevas features

Para agregar una feature nueva:

1. Calcularla en `generar_features()` de `feature_engineering.py`
2. Agregarla a `FEATURE_COLUMNS` en el mismo archivo
3. **Borrar los modelos existentes** en `IA_models/` — fueron entrenados con
   el número anterior de features y son incompatibles
4. Re-entrenar: `python main.py --entrenar --modo prod`

Si no se borran los modelos, la predicción fallará con:
```
ValueError: El modelo espera 41 features pero recibió 42
```

El número de features se guarda en `payload["n_features"]` de cada modelo .pkl,
lo que permite detectar incompatibilidades antes de intentar predecir.
