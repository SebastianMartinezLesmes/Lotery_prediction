# Machine Learning — Implementación y Estado

Documento técnico sobre el pipeline de ML: cómo funciona el entrenamiento,
qué produce, y cómo se consume en la predicción.

---

## Pipeline de entrenamiento

```
datos (Neon / Excel fallback)
        │
        ▼
feature_engineering.py → generar_features(df)
        │   41 features históricas → X (N × 41)
        ▼
training_simple.py → entrenar_modelos_por_loteria()
  ├── descompone result en 4 dígitos → y_miles, y_centenas, y_decenas, y_unidades
  ├── split TEMPORAL: X[:split_idx] train / X[split_idx:] test
  ├── [modo test]  random search, 2 iteraciones secuenciales
  ├── [modo prod]  algoritmo genético: 15 gen × 8 ind, paralelo con threads
  ├── evalúa cada individuo: acc_result = media(acc_miles,cent,dec,uni)
  ├── early stop si no mejora el best global en 5 generaciones
  └── guarda en IA_models/ solo si supera accuracy del peor slot
        │
        ▼
IA_models/
  ├── 1_astro_luna_result.pkl  ← _ModeloCompuesto (4 RF internos)
  ├── 2_astro_luna_result.pkl  ← slot alternativo
  ├── 1_astro_luna_series.pkl  ← RandomForestClassifier (12 clases zodiacales)
  └── 2_astro_luna_series.pkl  ← slot alternativo
```

---

## Modos de entrenamiento

Controlado por `TRAINING_MODE` en `.env` o por `--modo` en CLI.

### test

```
max_iter       : 2
n_jobs         : 1 (secuencial)
n_estimators   : [20, 30]
max_depth      : [3, 4]
min_samples_split: [4]
test_size      : 0.30
min_records    : 20
```

Objetivo: verificar que el pipeline funciona end-to-end en segundos.
No produce modelos de calidad producción.

### prod

```
generaciones   : 15       (número de generaciones del algoritmo genético)
poblacion      : 8        (individuos por generación)
elite          : 2        (individuos que pasan directos a la siguiente gen)
prob_mutacion  : 0.3      (probabilidad de mutar cada gen)
patience       : 5        (generaciones sin mejora antes del early stop)
n_jobs         : -1       (todos los núcleos disponibles)
n_estimators   : [100, 150, 200, 250, 300]
max_depth      : [4, 5, 6, 8, None]
min_samples_split: [2, 3, 5, 7]
test_size      : 0.20
min_records    : 50
```

Objetivo: encontrar la mejor combinación de hiperparámetros.
Tiempo típico: 4-6 minutos con 4 núcleos.

Para cambiar el perfil `prod`, editar `src/core/config.py` → `_TRAINING_PROFILES["prod"]`.

---

## Algoritmo genético vs. Random Search

El pipeline principal (`training_simple.py`) usa un **algoritmo genético real**
en modo prod, no random search:

| Propiedad | Random Search | Algoritmo Genético |
|---|---|---|
| Cada candidato | Completamente aleatorio | Hereda de los mejores anteriores |
| Mutación | Salto completo al azar | Paso ±1 en la lista de opciones (local) |
| Cruce | No aplica | Uniforme por gen: padre1 o padre2 con p=0.5 |
| Convergencia | Lenta, uniforme | Rápida, explota las mejores regiones |
| Diversidad | Alta siempre | Controlada por mutación y pool del top-50% |

El módulo legacy `src/utils/mutation.py` implementa una variante más compleja
que soporta RF, XGBoost y LightGBM, pero no está integrada en el pipeline principal.

---

## Split temporal

El split de evaluación es **cronológico**, no aleatorio:

```python
split_idx = int(n * (1 - test_size))  # test_size = 0.20
X_tr, X_te = X[:split_idx], X[split_idx:]
```

Esto significa que el modelo siempre se evalúa sobre los sorteos más recientes,
que son los que no vio durante el entrenamiento. Es la única forma honesta de
medir el rendimiento en una serie temporal.

**Comparación:**

| Split | ¿Usa datos futuros para entrenar? | ¿Accuracy confiable? |
|---|---|---|
| Aleatorio (80/20) | Sí (puede) | No — sobreestimado |
| Temporal (80/20) | No | Sí — representativo |
| Backtesting sorteo a sorteo | No | Sí — el más honesto |

El backtesting sorteo a sorteo (el más honesto) está pendiente de implementar.
Ver `Docs/Task_backtesting.md`.

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
candidatos = [
    (m*1000 + c*100 + d*10 + u,  pm * pc * pd * pu)
    for m, pm in top_k(self.miles)      # top 2 dígitos de miles
    for c, pc in top_k(self.centenas)
    for d, pd in top_k(self.decenas)
    for u, pu in top_k(self.unidades)   # 2^4 = 16 combinaciones
]
candidatos.sort(key=lambda x: x[1], reverse=True)
return candidatos[:3]
```

**Ventaja**: reduce 909 clases a 4 problemas de 10 clases.
**Limitación**: asume independencia entre dígitos (correlación ≈ 0 en los datos).

---

## Línea base de accuracy

Al finalizar cada entrenamiento, `training_simple.py` calcula e imprime:

```python
from collections import Counter
baseline_result = max(Counter(y_result % 10).values()) / len(y_result)
baseline_series = max(Counter(y_series).values()) / len(y_series)
print(f"  Modelo result: {mejor_acc_result:.2%} | Línea base: {baseline_result:.2%}")
print(f"  Modelo series: {mejor_acc_series:.2%} | Línea base: {baseline_series:.2%}")
```

**Nota**: `baseline_result` usa `y_result % 10` (dígito de unidades), no el resultado
completo. Esto mide la clase más frecuente del dígito de unidades, no del número de
4 dígitos. Para la línea base de número exacto, el azar puro es ≈ 0.11% (1/909 clases).

---

## Sistema de slots (Memoria IA)

Cada lotería tiene 2 slots por tipo de modelo:

```
IA_models/
  1_<loteria>_result.pkl   ← primer slot de result
  2_<loteria>_result.pkl   ← segundo slot de result
  1_<loteria>_series.pkl   ← primer slot de series
  2_<loteria>_series.pkl   ← segundo slot de series
```

Al guardar un nuevo modelo, `save_training.py`:
1. Busca el slot con menor accuracy (o el primer slot vacío)
2. Si el nuevo modelo **supera** ese accuracy, lo reemplaza con metadata completa
3. Si no supera, no hace nada (`↔ Sin mejora`)

Al cargar para predicción, `prediction.py` selecciona el slot con mayor accuracy.

---

## Métricas actuales

Resultados de entrenamiento modo prod sobre ASTRO LUNA:

| Métrica | Valor |
|---|---|
| Result accuracy (split temporal) | ~0.25 |
| Series accuracy (split temporal) | ~0.14 |
| Generaciones hasta early stop | ~5-15/15 |
| Tiempo total (4 núcleos) | ~4-6 min |

Referencia de azar puro:
- Result (número exacto): ~0.001 (1/909 clases)
- Series (signo zodiacal): ~0.083 (1/12 signos)

---

## Predicción

El motor de predicción (`prediction.py`) sigue estos pasos:

1. Carga el slot con mayor accuracy para cada tipo (result y series)
2. Genera las 41 features sobre el historial completo de la lotería
3. Toma la **última fila** del DataFrame de features (= estado más reciente)
4. Verifica compatibilidad: `features.shape[1] == modelo_result.n_features_in_`
5. Llama a `top3_numeros()` del `_ModeloCompuesto` → top-3 números con probabilidad conjunta
6. Llama a `predict_proba()` del modelo de series → top-3 signos con probabilidad
7. Guarda en `data/results.json` con timestamp e imprime en consola

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

---

## Próximas mejoras priorizadas

| Mejora | Estado | Impacto estimado | Esfuerzo |
|---|---|---|---|
| Backtesting temporal (sorteo a sorteo) | PENDIENTE | Métricas más honestas | Alto |
| XGBoost/LightGBM como clasificador base | PENDIENTE | +2-5% accuracy | Medio |
| Features de dígitos para lag4 y lag5 | PENDIENTE | +1-2% accuracy | Bajo |
| Ajuste de umbrales del sistema de alertas | PENDIENTE | UX más útil | Bajo |
| Calibración de probabilidades | PENDIENTE | Confianza más realista | Medio |
| Entrenar modelos para ASTRO SOL | PENDIENTE | Nueva lotería cubierta | Bajo |
