# Estado del Sistema de IA

Descripción del estado actual del sistema de inteligencia artificial,
decisiones tomadas y líneas de mejora futuras.

---

## Estado actual

| Componente | Estado |
|---|---|
| Algoritmo base | RandomForest (modelo compuesto por dígitos) |
| Features | 41 históricas (sin calendario) |
| Entrenamiento | Algoritmo genético con paralelismo y early stopping |
| Modos | `test` (2 iter, secuencial) / `prod` (15 gen × 8 ind, paralelo) |
| Split de evaluación | **Temporal** (80% train / 20% test cronológico) |
| Memoria IA | 2 slots por modelo — guarda solo si supera accuracy previo |
| Predicción | Top-3 números + Top-3 signos con probabilidad conjunta |
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

### Por qué algoritmo genético en modo prod (no random search)

A diferencia del random search (donde cada candidato es completamente independiente),
el algoritmo genético **hereda y refina** los mejores hiperparámetros encontrados:

- Ciclo por generación: evaluar en paralelo → ordenar → conservar 2 élite → cruzar top-50% + mutar
- La mutación es **local** (paso ±1 en la lista de opciones), no un salto aleatorio
- Early stop si no mejora el mejor global en 5 generaciones consecutivas

Esto converge más rápido que el random search en el espacio de ~100 combinaciones posibles.

### Por qué split temporal y no aleatorio

**Implementado en la versión actual**: `training_simple.py` usa corte cronológico:

```python
split_idx = int(n * (1 - test_size))  # test_size = 0.20 en prod
X_tr, X_te = X[:split_idx], X[split_idx:]
```

Los primeros 80% (registros más antiguos) son train set.
Los últimos 20% (registros más recientes) son test set.

Esto garantiza que el modelo nunca usa datos futuros para evaluar el rendimiento
del pasado. Un split aleatorio podría usar datos del futuro para entrenar
(ej. sorteo del 1 de mayo en train, pero del 15 de abril en test), lo que
sobreestimaría la capacidad real del modelo.

### Por qué paralelismo con threads en vez de processes

`joblib.Parallel(prefer="threads")` evita el overhead de serialización que tiene
`prefer="processes"`. RandomForest libera el GIL durante el entrenamiento (opera
en C/Cython), así que los threads sí corren en paralelo real en este caso.

---

## Señal estadística detectada en los datos

Análisis sobre ASTRO LUNA:

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

### 1. Backtesting temporal real (PENDIENTE)

Ver `Docs/Task_backtesting.md` para la especificación completa.

El entrenamiento ya usa un split temporal correcto. Lo que falta es la evaluación
**sorteo por sorteo** sobre los últimos N sorteos (ventana deslizante), para medir
el accuracy real que hubiera tenido el modelo en producción.

El script `scripts/backtesting.py` está especificado pero **no implementado**.

### 2. GradientBoosting como clasificador alternativo

XGBoost y LightGBM **ya están en `requirements.txt`** y disponibles en
`src/utils/mutation.py` (entrenamiento legacy). No están integrados en el
pipeline principal `training_simple.py`.

Para integrarlo: agregar XGB/LGBM como opción de clasificador base en el perfil
`prod` de `config.py` y adaptar `_ModeloCompuesto` en `training_simple.py`.

**Impacto esperado: +2-5% accuracy.**

### 3. Features de dígitos para lag4 y lag5

Actualmente se extraen los 4 dígitos de lag1, lag2 y lag3 (12 features en total).
Extender a lag4 y lag5 añadiría 8 features más (total: 49 features).

**Requiere**: borrar y re-entrenar todos los modelos existentes en `IA_models/`.
**Impacto estimado: +1-2% accuracy.**

### 4. Calibración de probabilidades

Las probabilidades del top-3 (ej. 18.33% para el primer candidato) pueden
estar sobre-estimadas. `CalibratedClassifierCV` de sklearn alinea las
probabilidades predichas con las frecuencias reales observadas.

**Impacto**: confianza más realista para el usuario, útil para decidir cuántos
números jugar. Sin impacto en el accuracy del top-1.

### 5. Ajuste de umbrales del sistema de alertas

Los umbrales actuales de `alerts.py` (WARNING=0.60, CRITICAL=0.50) están
pensados para modelos de alta precisión y siempre se disparan con el accuracy
real del modelo (~0.25). Deberían ajustarse a valores realistas para este
dominio (ej. WARNING=0.15, CRITICAL=0.10).

---

## Lo que NO vale la pena implementar

| Idea | Por qué no |
|---|---|
| Redes neuronales (LSTM) | ~1000 registros es insuficiente para entrenar una RNN útil |
| Más ventanas rolling (14, 60 días) | Redundante con las ventanas 7 y 30 ya presentes |
| Features de signo zodiacal para predecir el número | Número y signo son independientes |
| Lags muy lejanos (lag_15, lag_20) | La señal decae rápido; lag_7 ya captura lo relevante |
| Ciclos lunares / features astronómicas | No hay correlación estadística con los resultados |

---

## Límite teórico de accuracy

Con datos verdaderamente aleatorios y ~909 clases, el azar puro da ~0.11%.
El sistema actual logra ~25% con el split temporal, lo que confirma que
**existen patrones explotables** en los datos, principalmente la reversión
a la media y la estructura de dígitos.

El backtesting real (sorteo a sorteo) podría dar una cifra diferente, posiblemente
menor, ya que el split temporal de entrenamiento también puede tener pequeños
efectos de memorización. Ver `Docs/Task_backtesting.md`.

El límite práctico estimado con los datos disponibles es ~30-35% para result
y ~20-25% para series, considerando el nivel de ruido inherente del fenómeno.

---

## Sistema de alertas

`src/utils/alerts.py` proporciona `AlertManager` con:

- Verificación de accuracy y F1 contra umbrales configurables (WARNING/CRITICAL)
- Salida a consola con símbolos visuales
- Notificación opcional por email (SMTP con TLS, desactivado por defecto)
- Historial en memoria de alertas de la sesión actual

```env
ALERT_ACCURACY_WARNING=0.6     # alerta si accuracy < 0.60
ALERT_ACCURACY_CRITICAL=0.5    # alerta CRITICAL si accuracy < 0.50
ALERT_EMAIL_ENABLED=false       # activar envío por email
ALERT_SMTP_SERVER=smtp.gmail.com
ALERT_EMAIL_SENDER=tu@email.com
ALERT_EMAIL_RECIPIENTS=destinatario@email.com
```

**Nota**: los umbrales predeterminados (0.6 y 0.5) están por encima del accuracy
real del modelo (~0.25), por lo que siempre disparan WARNING en cada entrenamiento.
Ver mejora #5 arriba.
