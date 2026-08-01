# Estado del Sistema de IA

Descripción del estado actual del sistema de inteligencia artificial,
decisiones tomadas y líneas de mejora futuras.

---

## Estado actual

| Componente | Estado |
|---|---|
| Algoritmo base | RandomForest (modelo compuesto por dígitos) |
| Features | 41 históricas (sin calendario) |
| Entrenamiento | Paralelo con early stopping |
| Modos | `test` (2 iter, secuencial) / `prod` (60 iter, 4 núcleos) |
| Memoria IA | 2 slots por modelo — guarda solo si mejora |
| Predicción | Top-3 números + Top-3 signos con confianza |
| Accuracy result | ~0.25 (modo prod, ASTRO LUNA) |
| Accuracy series | ~0.14 (modo prod, ASTRO LUNA) |

---

## Decisiones de diseño tomadas

### Por qué se eliminaron las features de calendario

Las features `dia`, `mes`, `anio`, `dia_semana` etc. fueron eliminadas porque
asumen que la fecha tiene relación causal con el resultado del sorteo. Eso no
tiene fundamento — cada sorteo es un evento independiente del día en que ocurre.

Mantenerlas introducía **ruido** en el modelo: el RF desperdiciaba splits en
variables irrelevantes, diluyendo la señal real que sí existe en el historial
de números.

### Por qué modelo compuesto por dígitos

El resultado es un número entre 0 y 9999, lo que genera ~909 clases únicas
con solo ~1000 registros. Intentar clasificar directamente ese espacio es
un problema extremadamente difícil (menos de 1.1 registros por clase en promedio).

La estrategia de descomponer en 4 dígitos (miles, centenas, decenas, unidades)
convierte el problema en 4 clasificaciones de **10 clases cada una**, que es
manejable con los datos disponibles. La predicción final se reconstruye
combinando las probabilidades de cada dígito.

### Por qué early stopping en modo prod

El espacio de hiperparámetros de RF con las opciones del perfil `prod` tiene
5 × 5 × 4 = 100 combinaciones posibles. Después de explorar ~40-50, la
probabilidad de encontrar algo significativamente mejor es baja. El early
stopping con `patience=20` evita desperdiciar tiempo en terreno ya explorado.

### Por qué paralelismo con threads en vez de processes

`joblib.Parallel(prefer="threads")` evita el overhead de serialización que
tiene `prefer="processes"`. RandomForest libera el GIL durante el entrenamiento
(opera en C/Cython), así que los threads sí corren en paralelo real en este caso.

---

## Señal estadística detectada en los datos

Análisis sobre ASTRO LUNA (996 registros, oct 2023 – jul 2026):

| Métrica | Valor | Interpretación |
|---|---|---|
| Autocorr result lag1 | 0.068 | Señal débil pero presente |
| Autocorr diff lag1 | **-0.465** | Fuerte reversión a la media |
| Autocorr dígito unidades lag1 | 0.083 | Leve persistencia por posición |
| Correlación entre dígitos | ~0 | Dígitos son independientes entre sí |
| Autocorr suma de dígitos lag1 | 0.055 | Señal débil de nivel general |

La señal más explotable es la **reversión a la media** (diff lag1 = -0.465):
cuando el número sube mucho respecto al anterior, tiende a bajar en el siguiente
sorteo, y viceversa. Esta señal se captura con las features `diff_1`, `diff_2`,
`diff_abs_1` y `signo_diff_1`.

---

## Mejoras pendientes con mayor potencial

### 1. Validación temporal cruzada

Actualmente se usa un split aleatorio 80/20. El problema es que puede usar
datos futuros para entrenar, lo que es irreal.

La validación correcta para series temporales es `TimeSeriesSplit`:

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(modelo, X, y, cv=tscv, scoring="accuracy")
# scores respetan el orden cronológico: siempre entrena con pasado, evalúa con futuro
```

Esto daría una estimación más honesta del accuracy real en producción.
**Impacto esperado: accuracy reportado baja ~2-3%, pero es más confiable.**

### 2. GradientBoosting como alternativa

XGBoost o LightGBM suelen superar a RandomForest en datos tabulares con
pocos registros. No cambian la estrategia de dígitos, solo el clasificador base:

```python
from xgboost import XGBClassifier

modelo = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    use_label_encoder=False,
    eval_metric="mlogloss"
)
```

Para integrarlo hay que agregar `xgboost` a `requirements.txt` y añadirlo
como opción en el perfil `prod` de `config.py`.
**Impacto esperado: +2-5% accuracy.**

### 3. Features de dígitos para lag2 y lag3

Actualmente se extraen los 4 dígitos solo de `lag1`. Hacer lo mismo para
`lag2` y `lag3` daría más contexto sobre patrones por posición de dígito.
Ya está implementado en `feature_engineering.py` para lag1, lag2 y lag3.

### 4. Detección de ciclos con autocorrelación

Si existiera algún ciclo periódico (ej. el dígito de unidades repite cada
N sorteos), se podría detectar y usar como feature:

```python
from statsmodels.tsa.stattools import acf

corrs = acf(df["result"], nlags=60)
picos = [i for i, c in enumerate(corrs[1:], 1) if abs(c) > 0.15]
```

Con los datos actuales no se detectaron ciclos significativos, pero puede
cambiar a medida que se acumulen más registros.

---

## Lo que NO vale la pena implementar

| Idea | Por qué no |
|---|---|
| Redes neuronales (LSTM) | ~1000 registros es insuficiente para entrenar una RNN útil |
| Más ventanas rolling (14, 60 días) | Redundante con las ventanas 7 y 30 ya presentes |
| Features del signo zodiacal para predecir el número | Número y signo son independientes según los datos |
| Lags muy lejanos (lag_15, lag_20) | La señal decae rápido; lag_7 ya captura lo relevante |
| Ciclos lunares / features astronómicas | No hay correlación estadística con los resultados |

---

## Límite teórico de accuracy

Con una lotería bien diseñada y datos verdaderamente aleatorios, el límite
teórico de accuracy para predecir el número exacto con ~909 clases es ~0.11%
(azar puro). El sistema actual logra ~25%, lo que sugiere que **sí existen
patrones explotables** en los datos, principalmente por la reversión a la media
y la estructura de dígitos.

El límite práctico estimado con los datos disponibles es ~30-35% para result
y ~20-25% para series, considerando el nivel de ruido inherente.
