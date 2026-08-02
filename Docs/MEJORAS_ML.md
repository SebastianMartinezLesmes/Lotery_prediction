# Machine Learning — Implementación y Estado

Documento técnico sobre el pipeline de ML: cómo funciona el entrenamiento,
qué produce, y cómo se consume en la predicción.

---

## Pipeline de entrenamiento

```
datos (Neon / Excel)
        │
        ▼
feature_engineering.py   →  41 features históricas  →  X (N × 41)
        │
        ▼
training_simple.py
  ├── descompone result en 4 dígitos  →  y_miles, y_centenas, y_decenas, y_unidades
  ├── genera N combinaciones de hiperparámetros (n_est, depth, split, seed)
  ├── [modo test]  ejecuta 2 iteraciones secuenciales
  ├── [modo prod]  ejecuta en lotes de 4 (n_jobs=CPU), con early stopping patience=20
  ├── evalúa cada iteración: acc_result = media(acc_miles, acc_cent, acc_dec, acc_uni)
  └── guarda en IA_models/ solo si supera el modelo previo
        │
        ▼
IA_models/
  ├── 1_astro_luna_result.pkl  ←  _ModeloCompuesto (4 RF internos)
  ├── 2_astro_luna_result.pkl  ←  slot alternativo
  ├── 1_astro_luna_series.pkl  ←  RandomForestClassifier (12 clases zodiacales)
  └── 2_astro_luna_series.pkl  ←  slot alternativo
```

---

## Modos de entrenamiento

Controlado por `TRAINING_MODE` en `.env` o por `--modo` en CLI.

### test

```
Iteraciones : 2
n_jobs      : 1 (secuencial)
n_estimators: [20, 30]
max_depth   : [3, 4]
test_size   : 0.30
min_records : 20
```

Objetivo: verificar que el pipeline funciona end-to-end en segundos.
No produce modelos de calidad producción.

### prod

```
Iteraciones : 60 (máximo, puede parar antes por early stop)
n_jobs      : -1 (todos los núcleos disponibles — actualmente 4)
n_estimators: [100, 150, 200, 250, 300]
max_depth   : [4, 5, 6, 8, None]
min_samples_split: [2, 3, 5, 7]
test_size   : 0.20
patience    : 20 (early stop si no mejora en 20 iteraciones)
```

Objetivo: encontrar la mejor combinación de hiperparámetros.
Tiempo típico: 4-6 minutos con 4 núcleos.

Para cambiar el perfil `prod`, editar `src/core/config.py` → `_TRAINING_PROFILES["prod"]`.

---

## Modelo compuesto (_ModeloCompuesto)

El resultado de la lotería es un número 0-9999 con ~909 clases únicas.
Clasificar directamente ese espacio con ~1000 registros es inviable
(menos de 1.1 muestras por clase en promedio).

**Solución**: descomponer en 4 dígitos y entrenar un RF por posición.

```
result = 8335
         ├── miles    = 8   (10 clases: 0-9)
         ├── centenas = 3   (10 clases: 0-9)
         ├── decenas  = 3   (10 clases: 0-9)
         └── unidades = 5   (10 clases: 0-9)
```

Cada RF predice su dígito con `predict_proba`. La predicción final combina
las probabilidades multiplicadas para generar los top-3 números candidatos:

```python
# top_k devuelve [(dígito, probabilidad), ...]
candidatos = [
    (m*1000 + c*100 + d*10 + u,  pm * pc * pd * pu)
    for m, pm in top_k(self.miles)
    for c, pc in top_k(self.centenas)
    ...
]
candidatos.sort(key=lambda x: x[1], reverse=True)
return candidatos[:3]
```

**Ventaja**: reduce el problema de 909 clases a 4 problemas de 10 clases.
**Limitación**: asume independencia entre dígitos (correlación ≈ 0 en los datos actuales).

---

## Sistema de slots (Memoria IA)

Cada lotería tiene 2 slots por tipo de modelo:

```
IA_models/
  1_<loteria>_result.pkl   ← mejor modelo histórico
  2_<loteria>_result.pkl   ← segundo mejor modelo histórico
```

Al guardar un nuevo modelo, `save_training.py`:
1. Busca el slot con menor accuracy
2. Si el nuevo modelo **supera** ese accuracy, lo reemplaza
3. Si no supera, no hace nada (`↔ Sin mejora`)

Esto garantiza que `IA_models/` siempre contenga los 2 mejores modelos
encontrados en toda la historia de entrenamientos.

Al cargar para predicción, se usa el slot con mayor accuracy.

---

## Métricas actuales

Resultados de entrenamiento modo prod sobre ASTRO LUNA (996 registros):

| Métrica | Valor |
|---|---|
| Result accuracy | ~0.25 |
| Series accuracy | ~0.14 |
| Iteraciones hasta early stop | ~55/60 |
| Tiempo total (4 núcleos) | ~5 min |

Referencia de azar puro:
- Result: ~0.001 (1/909 clases)
- Series: ~0.083 (1/12 signos zodiacales)

El sistema supera el azar **250× en result** y **1.7× en series**.

---

## Predicción

El motor de predicción (`prediction.py`) sigue estos pasos:

1. Carga el mejor modelo disponible de cada slot
2. Genera las mismas 41 features sobre el historial completo
3. Toma la **última fila** del dataframe de features (= estado más reciente)
4. Llama a `top3_numeros()` del modelo compuesto → top-3 números con probabilidad
5. Llama a `predict_proba()` del modelo de series → top-3 signos con probabilidad
6. Guarda en `data/results.json` con timestamp

Output de ejemplo:
```
🎯 PREDICCIÓN
  Lotería : ASTRO LUNA
  Número  : 8335   Signo: LIB

  Top 3 números:
    8335  18.33%  ███
    8435   3.02%  █
    9335   2.48%  █

  Top 3 signos:
    LIB  16.76%  ███
    SAG   9.12%  █
    LEO   8.98%  █
```

La concentración de probabilidad en el top-1 (18% vs 3% el segundo)
indica que el modelo tiene alta certeza en los dígitos de posición 2, 3 y 4
pero incertidumbre en el primer dígito.

---

## Alertas de rendimiento

`alerts.py` verifica el accuracy después de cada entrenamiento y emite
alertas a consola (y opcionalmente por email) si cae bajo los umbrales:

| Nivel | Accuracy | F1 |
|---|---|---|
| WARNING | < 0.60 | < 0.55 |
| CRITICAL | < 0.50 | < 0.45 |

Configurables vía `.env`:
```env
ALERT_ACCURACY_WARNING=0.6
ALERT_ACCURACY_CRITICAL=0.5
ALERT_EMAIL_ENABLED=false
```

---

## Próximas mejoras priorizadas

| Mejora | Impacto estimado | Esfuerzo |
|---|---|---|
| Validación temporal (TimeSeriesSplit) | Métricas más honestas | Bajo |
| XGBoost como clasificador alternativo | +2-5% accuracy | Medio |
| Features de dígitos para lag4 y lag5 | +1-2% accuracy | Bajo |
| Calibración de probabilidades | Confianza más realista | Medio |
