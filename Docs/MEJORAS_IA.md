# Mejoras de IA y Algoritmo Genético

Estado actual del sistema y propuestas de mejora ordenadas por impacto.

---

## Estado Actual

- Algoritmo: RandomForest con búsqueda evolutiva (genética)
- Features: 20 (temporales, lag, rolling, tendencia, frecuencia)
- Memoria IA: 2 slots por modelo (result + series) en `IA_models/`
- Warm start: activo (carga el mejor modelo como baseline genético)
- Evaluación paralela: activa (`n_jobs=-1`)

---

## Mejoras Propuestas

### 1. Features (Mayor impacto inmediato)

El modelo actualmente usa 20 features. Agregar estas puede mejorar el score:

**Frecuencia histórica del número**
```python
# Cuántas veces apareció cada número en los últimos N sorteos
df["freq_result_30"] = df["result"].apply(
    lambda x: (df["result"].tail(30) == x).sum()
)
```

**Distancia al último sorteo del mismo número**
```python
# Cuántos días han pasado desde que salió este número
df["dias_desde_ultimo"] = df.groupby("result")["fecha"].diff().dt.days
```

**Número de dígitos (unidades, decenas, centenas, miles)**
```python
df["digito_unidad"]   = df["result"] % 10
df["digito_decena"]   = (df["result"] // 10) % 10
df["digito_centena"]  = (df["result"] // 100) % 10
df["digito_mil"]      = (df["result"] // 1000) % 10
```

**Paridad y divisibilidad**
```python
df["es_par"] = df["result"] % 2
df["suma_digitos"] = df["result"].astype(str).apply(lambda x: sum(int(d) for d in x))
```

**Ciclos lunares / estacionales**
```python
import math
df["ciclo_lunar"] = df["fecha"].apply(lambda d: math.sin(2 * math.pi * d.day / 29.5))
df["ciclo_anual"] = df["fecha"].apply(lambda d: math.sin(2 * math.pi * d.dayofyear / 365))
```

---

### 2. Algoritmo Genético (Mejoras al motor evolutivo)

**Diversidad genética controlada**

Actualmente la población puede converger prematuramente. Agregar un índice de diversidad:

```python
def calcular_diversidad(poblacion):
    n_estimators = [p["n_estimators"] for p in poblacion]
    return np.std(n_estimators)  # baja diversidad = estancamiento

# Si diversidad < umbral, inyectar individuos aleatorios
if calcular_diversidad(poblacion) < 10:
    poblacion[-3:] = crear_poblacion_inicial(3)
```

**Elitismo adaptativo**

En vez de siempre guardar los top-K, variar el tamaño del elite según la generación:

```python
elite_size = max(2, int(poblacion_size * (1 - generacion / max_generaciones) * 0.3))
```

**Torneo en vez de ranking**

La selección por torneo mantiene más diversidad que seleccionar siempre los mejores:

```python
def seleccion_torneo(resultados, k=3):
    torneo = random.sample(resultados, k)
    return max(torneo, key=lambda x: x["accuracy"])
```

**Crossover de múltiples puntos**

El crossover actual elige aleatoriamente entre padre1 y padre2. Un crossover de 2 puntos mezcla mejor:

```python
def crossover_2puntos(padre1, padre2):
    keys = list(padre1.keys())
    p1, p2 = sorted(random.sample(range(len(keys)), 2))
    hijo = {}
    for i, k in enumerate(keys):
        hijo[k] = padre1[k] if i < p1 or i >= p2 else padre2[k]
    return hijo
```

---

### 3. Modelos Alternativos (Reemplazar o complementar RandomForest)

**XGBoost** - Generalmente supera a RandomForest en datos tabulares:
```python
from xgboost import XGBClassifier
modelo = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1)
```

**LightGBM** - Más rápido que XGBoost, bueno para datasets pequeños:
```python
from lightgbm import LGBMClassifier
modelo = LGBMClassifier(n_estimators=200, num_leaves=31, verbose=-1)
```

**Ensemble de modelos** - Combinar predicciones de varios modelos:
```python
from sklearn.ensemble import VotingClassifier
ensemble = VotingClassifier([
    ("rf", RandomForestClassifier()),
    ("xgb", XGBClassifier()),
    ("lgbm", LGBMClassifier())
], voting="soft")
```

Para integrar en el sistema evolutivo, agregar en `config.py`:
```python
ALGORITMOS_DISPONIBLES = ["RandomForest", "XGBoost", "LightGBM"]
```

---

### 4. Memoria IA (Mejorar el sistema de slots)

Actualmente hay 2 slots por modelo. Propuesta: aumentar a 3 y agregar metadata:

```python
payload = {
    "model": modelo,
    "accuracy": float(accuracy),
    "f1_score": float(f1),
    "n_features": modelo.n_features_in_,
    "n_records_trained": len(X),
    "timestamp": datetime.now().isoformat(),
    "feature_names": list(feature_columns),
    "params": modelo.get_params()
}
```

Esto permite saber exactamente con qué features y parámetros se entrenó cada modelo guardado.

---

### 5. Validación del Modelo (Métricas más robustas)

Actualmente se usa accuracy en un solo split. Mejorar con validación cruzada temporal:

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(modelo, X, y, cv=tscv, scoring="accuracy")
acc_temporal = scores.mean()
```

Esto es más realista porque respeta el orden temporal de los datos (no usa datos futuros para entrenar).

---

### 6. Predicción con Confianza

Actualmente la predicción devuelve solo el número. Agregar probabilidad de confianza:

```python
proba = modelo.predict_proba(X_hoy)
top3 = np.argsort(proba[0])[-3:][::-1]  # top 3 candidatos

for idx in top3:
    numero = modelo.classes_[idx]
    confianza = proba[0][idx]
    print(f"  #{numero} → {confianza:.1%} de confianza")
```

---

### 7. Detección de Patrones Cíclicos

Los números de lotería pueden tener ciclos. Detectarlos con autocorrelación:

```python
from statsmodels.tsa.stattools import acf

correlaciones = acf(df["result"], nlags=30)
ciclos_detectados = [i for i, c in enumerate(correlaciones) if abs(c) > 0.1]
# Agregar como feature: días desde el último ciclo detectado
```

---

## Prioridad de Implementación

| # | Mejora | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 1 | Dígitos individuales como features | Alto | Bajo |
| 2 | Frecuencia histórica del número | Alto | Bajo |
| 3 | Validación cruzada temporal | Alto | Medio |
| 4 | XGBoost / LightGBM | Alto | Medio |
| 5 | Predicción con confianza (top 3) | Medio | Bajo |
| 6 | Diversidad genética controlada | Medio | Medio |
| 7 | Metadata en slots de memoria IA | Medio | Bajo |
| 8 | Crossover de 2 puntos | Bajo | Bajo |
| 9 | Detección de ciclos (autocorrelación) | Bajo | Alto |

---

## Ramas Git Recomendadas

```
main              → producción estable (solo merge desde develop)
develop           → integración de features en desarrollo
feature/features  → nuevas features de entrenamiento
feature/xgboost   → integración de XGBoost/LightGBM
feature/confianza → predicción con probabilidades
fix/xxx           → correcciones de bugs
experiment/xxx    → experimentos sin garantía de merge
```
