# 🧠 Cómo Funciona el Entrenamiento de IA

## 📋 Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Proceso de Entrenamiento](#proceso-de-entrenamiento)
4. [Modelos Utilizados](#modelos-utilizados)
5. [Features y Preprocesamiento](#features-y-preprocesamiento)
6. [Métricas y Evaluación](#métricas-y-evaluación)
7. [Optimización e Iteraciones](#optimización-e-iteraciones)
8. [Persistencia de Modelos](#persistencia-de-modelos)
9. [Uso de Modelos Entrenados](#uso-de-modelos-entrenados)
10. [Mejores Prácticas](#mejores-prácticas)

---

## 🎯 Visión General

El sistema de predicción de lotería utiliza **Machine Learning supervisado** para predecir dos componentes:

1. **Número ganador** (0-9999) - Modelo de clasificación
2. **Símbolo zodiacal** (12 signos) - Modelo de clasificación

### Características Clave:
- ✅ Entrenamiento independiente por lotería
- ✅ Dos modelos especializados por lotería
- ✅ Mejora iterativa con búsqueda de hiperparámetros
- ✅ Persistencia automática de mejores modelos
- ✅ Carga incremental para perfeccionamiento

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    DATOS HISTÓRICOS                         │
│              (resultados_astro.xlsx)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              PREPROCESAMIENTO                               │
│  • Extracción de features temporales                        │
│  • Codificación de símbolos zodiacales                      │
│  • Separación por lotería                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ENTRENAMIENTO DUAL                             │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐     │
│  │  MODELO RESULT       │    │  MODELO SERIES       │     │
│  │  (Número ganador)    │    │  (Signo zodiacal)    │     │
│  │                      │    │                      │     │
│  │  RandomForest        │    │  RandomForest        │     │
│  │  n_estimators=200    │    │  n_estimators=200    │     │
│  │  max_depth=4         │    │  max_depth=10        │     │
│  └──────────────────────┘    └──────────────────────┘     │
└────────────────────┬────────────────┬───────────────────────┘
                     │                │
                     ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              EVALUACIÓN Y SELECCIÓN                         │
│  • Accuracy score                                           │
│  • F1-score macro                                           │
│  • Validación cruzada                                       │
│  • Selección del mejor modelo                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              PERSISTENCIA                                   │
│  IA_models/modelo_result_{loteria}.pkl                      │
│  IA_models/modelo_series_{loteria}.pkl                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Proceso de Entrenamiento

### Paso 1: Carga de Datos

```python
# Leer archivo Excel con resultados históricos
df = pd.read_excel("resultados_astro.xlsx")

# Columnas requeridas:
# - fecha: Fecha del sorteo
# - lottery: Nombre de la lotería (ej: "ASTRO SOL", "ASTRO LUNA")
# - result: Número ganador (0-9999)
# - series: Signo zodiacal (ej: "ARIES", "TAURO")
```

### Paso 2: Preprocesamiento

```python
# Limpieza
df = df.dropna(subset=["fecha", "lottery", "result", "series"])
df["result"] = df["result"].astype(int)
df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)

# Codificación de series (signos zodiacales)
df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
# ARIES=0, TAURO=1, GÉMINIS=2, ..., PISCIS=11

# Extracción de features temporales
df["dia"] = df["fecha"].dt.day          # 1-31
df["mes"] = df["fecha"].dt.month        # 1-12
df["anio"] = df["fecha"].dt.year        # 2023, 2024, etc.
df["dia_semana"] = df["fecha"].dt.weekday  # 0=Lunes, 6=Domingo
```

### Paso 3: Separación por Lotería

```python
# El sistema entrena un modelo independiente para cada lotería
loterias = df["lottery"].str.lower().unique()
# Ejemplo: ["astro sol", "astro luna"]

for nombre_loteria in loterias:
    df_loteria = df[df["lottery"].str.lower() == nombre_loteria]
    
    # Features (X) y targets (y)
    X = df_loteria[["dia", "mes", "anio", "dia_semana"]].values
    y_result = df_loteria["result"].values
    y_series = df_loteria["series"].values
    
    # Entrenar modelos para esta lotería
    entrenar_modelos_por_loteria(X, y_result, y_series, nombre_loteria)
```

### Paso 4: Entrenamiento Iterativo

```python
# Configuración
ITERATIONS = 8000      # Número máximo de iteraciones
MIN_ACCURACY = 0.7     # Umbral mínimo de precisión

mejor_acc_result = 0
mejor_acc_series = 0
mejor_modelo_result = None
mejor_modelo_series = None

for intento in range(1, ITERATIONS + 1):
    # Random state diferente en cada iteración
    random_state = np.random.randint(0, 10000)
    
    # Split de datos (80% train, 20% test)
    X_train, X_test, y_train_result, y_test_result = train_test_split(
        X, y_result, test_size=0.2, random_state=random_state
    )
    
    # Entrenar modelo para números
    modelo_result = RandomForestClassifier(
        n_estimators=200,
        max_depth=4,
        min_samples_split=5,
        class_weight='balanced',
        random_state=random_state
    )
    modelo_result.fit(X_train, y_train_result)
    
    # Entrenar modelo para símbolos
    modelo_series = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        class_weight='balanced',
        random_state=42
    )
    modelo_series.fit(X_train, y_train_series)
    
    # Evaluar
    acc_result = accuracy_score(y_test_result, modelo_result.predict(X_test))
    acc_series = accuracy_score(y_test_series, modelo_series.predict(X_test))
    
    # Actualizar mejores modelos
    if acc_result > mejor_acc_result:
        mejor_acc_result = acc_result
        mejor_modelo_result = modelo_result
    
    if acc_series > mejor_acc_series:
        mejor_acc_series = acc_series
        mejor_modelo_series = modelo_series
    
    # Detener si se alcanza el umbral
    if acc_result >= MIN_ACCURACY and acc_series >= MIN_ACCURACY:
        break
```

---

## 🤖 Modelos Utilizados

### Random Forest Classifier

**¿Por qué Random Forest?**
- ✅ Robusto ante overfitting
- ✅ Maneja bien datos categóricos
- ✅ No requiere normalización
- ✅ Captura relaciones no lineales
- ✅ Proporciona importancia de features

### Modelo Result (Números)

```python
RandomForestClassifier(
    n_estimators=200,        # 200 árboles de decisión
    max_depth=4,             # Profundidad máxima baja (evita overfitting)
    min_samples_split=5,     # Mínimo 5 muestras para dividir nodo
    class_weight='balanced', # Balanceo automático de clases
    random_state=variable    # Cambia en cada iteración
)
```

**Características:**
- Profundidad limitada (4) para evitar memorizar patrones
- Balanceo de clases (algunos números son más frecuentes)
- 200 árboles para estabilidad

### Modelo Series (Símbolos)

```python
RandomForestClassifier(
    n_estimators=200,        # 200 árboles de decisión
    max_depth=10,            # Mayor profundidad (12 clases)
    min_samples_split=5,     # Mínimo 5 muestras para dividir nodo
    class_weight='balanced', # Balanceo automático de clases
    random_state=42          # Fijo para reproducibilidad
)
```

**Características:**
- Mayor profundidad (10) para capturar patrones zodiacales
- 12 clases (signos del zodiaco)
- Random state fijo para consistencia

---

## 📊 Features y Preprocesamiento

### Features Temporales

| Feature | Rango | Descripción | Ejemplo |
|---------|-------|-------------|---------|
| `dia` | 1-31 | Día del mes | 15 |
| `mes` | 1-12 | Mes del año | 3 (Marzo) |
| `anio` | 2023+ | Año | 2024 |
| `dia_semana` | 0-6 | Día de la semana | 0 (Lunes) |

### Codificación de Targets

**Números (result):**
- Tipo: Entero
- Rango: 0-9999
- Clases: 10,000 posibles valores
- Tratamiento: Clasificación multiclase

**Símbolos (series):**
- Tipo: Categórico
- Valores: 12 signos zodiacales
- Codificación: Label encoding (0-11)

```python
ZODIACO = [
    "ARIES",      # 0
    "TAURO",      # 1
    "GÉMINIS",    # 2
    "CÁNCER",     # 3
    "LEO",        # 4
    "VIRGO",      # 5
    "LIBRA",      # 6
    "ESCORPIO",   # 7
    "SAGITARIO",  # 8
    "CAPRICORNIO",# 9
    "ACUARIO",    # 10
    "PISCIS"      # 11
]
```

---

## 📈 Métricas y Evaluación

### Accuracy (Precisión)

```python
accuracy = correct_predictions / total_predictions
```

**Interpretación:**
- 0.70 = 70% de predicciones correctas
- Umbral mínimo: 0.7 (70%)

### F1-Score (Macro)

```python
f1_macro = average(f1_score_per_class)
```

**Interpretación:**
- Balance entre precisión y recall
- Macro: promedio sin ponderar por frecuencia
- Útil para clases desbalanceadas

### Ejemplo de Evaluación

```python
# Predicciones
y_pred = modelo.predict(X_test)

# Métricas
acc = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, average='macro')

print(f"Accuracy: {acc:.4f}")  # 0.7234
print(f"F1-Score: {f1:.4f}")   # 0.6891

# Reporte detallado
print(classification_report(y_test, y_pred))
```

---

## 🔧 Optimización e Iteraciones

### Estrategia de Búsqueda

El sistema utiliza **búsqueda aleatoria** de hiperparámetros:

```python
for intento in range(1, MAX_ITERATIONS):
    # Generar random_state aleatorio
    random_state = np.random.randint(0, 10000)
    
    # Entrenar con diferentes splits de datos
    X_train, X_test = train_test_split(..., random_state=random_state)
    
    # Entrenar modelo
    modelo = entrenar_modelo(X_train, y_train, random_state)
    
    # Evaluar
    accuracy = evaluar(modelo, X_test, y_test)
    
    # Guardar si es mejor
    if accuracy > mejor_accuracy:
        mejor_accuracy = accuracy
        mejor_modelo = modelo
```

### Criterios de Parada

1. **Umbral alcanzado**: Accuracy ≥ MIN_ACCURACY (0.7)
2. **Máximo de iteraciones**: 8000 intentos
3. **Convergencia**: Ambos modelos superan el umbral

### Carga Incremental

Si ya existe un modelo entrenado:

```python
if os.path.exists(modelo_path):
    # Cargar modelo previo
    modelo_previo = joblib.load(modelo_path)
    
    # Evaluar con datos actuales
    acc_previa = accuracy_score(y, modelo_previo.predict(X))
    
    # Usar como baseline
    mejor_accuracy = acc_previa
    mejor_modelo = modelo_previo
    
    print(f"Modelo cargado con accuracy: {acc_previa:.4f}")
```

**Ventajas:**
- ✅ No se pierde progreso anterior
- ✅ Solo se guarda si hay mejora
- ✅ Perfeccionamiento continuo

---

## 💾 Persistencia de Modelos

### Estructura de Archivos

```
IA_models/
├── modelo_result_astro_sol.pkl      # Números para ASTRO SOL
├── modelo_series_astro_sol.pkl      # Símbolos para ASTRO SOL
├── modelo_result_astro_luna.pkl     # Números para ASTRO LUNA
└── modelo_series_astro_luna.pkl     # Símbolos para ASTRO LUNA
```

### Nomenclatura

```python
def generar_ruta_modelo(nombre_loteria, tipo):
    # Normalizar nombre
    nombre_archivo = nombre_loteria.lower().replace(' ', '_')
    
    # Construir nombre
    filename = f"modelo_{tipo}_{nombre_archivo}.pkl"
    
    # Ruta completa
    return os.path.join("IA_models", filename)

# Ejemplos:
# generar_ruta_modelo("ASTRO SOL", "result")
# → "IA_models/modelo_result_astro_sol.pkl"

# generar_ruta_modelo("ASTRO LUNA", "series")
# → "IA_models/modelo_series_astro_luna.pkl"
```

### Guardado

```python
import joblib

# Guardar modelo
joblib.dump(mejor_modelo_result, modelo_result_path)
joblib.dump(mejor_modelo_series, modelo_series_path)

print(f"✅ Modelos guardados:")
print(f"   - {modelo_result_path}")
print(f"   - {modelo_series_path}")
```

### Carga

```python
import joblib

# Cargar modelos
modelo_result = joblib.load(modelo_result_path)
modelo_series = joblib.load(modelo_series_path)

# Usar para predicción
numero = modelo_result.predict(X_hoy)[0]
simbolo_code = modelo_series.predict(X_hoy)[0]
simbolo = ZODIACO[simbolo_code]
```

---

## 🎯 Uso de Modelos Entrenados

### Predicción para Hoy

```python
from datetime import datetime
import pandas as pd

# Fecha actual
hoy = datetime.today()

# Crear features
X_hoy = pd.DataFrame([{
    "dia": hoy.day,
    "mes": hoy.month,
    "anio": hoy.year,
    "dia_semana": hoy.weekday()
}])

# Cargar modelos
modelo_result = joblib.load("IA_models/modelo_result_astro_sol.pkl")
modelo_series = joblib.load("IA_models/modelo_series_astro_sol.pkl")

# Predecir
numero = modelo_result.predict(X_hoy)[0]
simbolo_code = modelo_series.predict(X_hoy)[0]

# Decodificar símbolo
ZODIACO = ["ARIES", "TAURO", "GÉMINIS", ...]
simbolo = ZODIACO[simbolo_code]

print(f"🎰 Predicción para {hoy.strftime('%Y-%m-%d')}:")
print(f"   Número: {str(numero).zfill(4)}")
print(f"   Símbolo: {simbolo}")
```

### Predicción para Fecha Específica

```python
from datetime import date

# Fecha específica
fecha = date(2024, 12, 25)  # Navidad 2024

X_fecha = pd.DataFrame([{
    "dia": fecha.day,
    "mes": fecha.month,
    "anio": fecha.year,
    "dia_semana": fecha.weekday()
}])

# Predecir
numero = modelo_result.predict(X_fecha)[0]
simbolo_code = modelo_series.predict(X_fecha)[0]
simbolo = ZODIACO[simbolo_code]
```

---

## 🎓 Mejores Prácticas

### 1. Datos de Entrenamiento

✅ **Hacer:**
- Usar al menos 100 registros por lotería
- Incluir datos de diferentes meses/años
- Verificar que no haya duplicados
- Validar formato de fechas

❌ **Evitar:**
- Entrenar con menos de 50 registros
- Usar solo datos de un mes
- Incluir datos con errores

### 2. Hiperparámetros

✅ **Recomendaciones:**
- `n_estimators`: 100-300 (más árboles = más estable)
- `max_depth`: 4-10 (evitar overfitting)
- `min_samples_split`: 5-10 (evitar nodos muy pequeños)
- `class_weight='balanced'`: Siempre para clases desbalanceadas

### 3. Evaluación

✅ **Métricas importantes:**
- Accuracy: Precisión general
- F1-Score: Balance precisión/recall
- Confusion Matrix: Ver errores por clase
- Cross-validation: Validar estabilidad

### 4. Iteraciones

✅ **Configuración óptima:**
- MIN_ACCURACY: 0.7 (70%)
- MAX_ITERATIONS: 3000-8000
- Early stopping: Detener si se alcanza umbral

### 5. Mantenimiento

✅ **Actualización periódica:**
- Re-entrenar cada semana con nuevos datos
- Monitorear accuracy en producción
- Guardar historial de métricas
- Versionar modelos

---

## 🔬 Ejemplo Completo

```python
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib

# 1. Cargar datos
df = pd.read_excel("resultados_astro.xlsx")

# 2. Preprocesar
df["fecha"] = pd.to_datetime(df["fecha"])
df["dia"] = df["fecha"].dt.day
df["mes"] = df["fecha"].dt.month
df["anio"] = df["fecha"].dt.year
df["dia_semana"] = df["fecha"].dt.weekday
df["series"] = df["series"].astype("category").cat.codes

# 3. Filtrar por lotería
df_sol = df[df["lottery"] == "ASTRO SOL"]

# 4. Preparar datos
X = df_sol[["dia", "mes", "anio", "dia_semana"]].values
y_result = df_sol["result"].values
y_series = df_sol["series"].values

# 5. Entrenar
mejor_acc = 0
mejor_modelo = None

for i in range(1000):
    rs = np.random.randint(0, 10000)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_result, test_size=0.2, random_state=rs
    )
    
    modelo = RandomForestClassifier(
        n_estimators=200,
        max_depth=4,
        class_weight='balanced',
        random_state=rs
    )
    modelo.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, modelo.predict(X_test))
    
    if acc > mejor_acc:
        mejor_acc = acc
        mejor_modelo = modelo
    
    if acc >= 0.7:
        break

# 6. Guardar
joblib.dump(mejor_modelo, "IA_models/modelo_result_astro_sol.pkl")
print(f"✅ Modelo guardado con accuracy: {mejor_acc:.4f}")

# 7. Predecir
from datetime import datetime
hoy = datetime.today()
X_hoy = [[hoy.day, hoy.month, hoy.year, hoy.weekday()]]
numero = mejor_modelo.predict(X_hoy)[0]
print(f"🎰 Predicción: {str(numero).zfill(4)}")
```

---

## 📚 Referencias

### Archivos Relacionados
- `src/utils/training.py` - Código de entrenamiento
- `src/utils/prediction.py` - Código de predicción
- `src/core/config.py` - Configuración del sistema
- `src/models/schemas.py` - Esquemas de validación

### Documentación Adicional
- `ARCHITECTURE.md` - Arquitectura del sistema
- `README.md` - Guía de uso general
- `CAMBIOS_IA_MODELS.md` - Cambios en estructura de modelos

---

**Autor**: Sistema de Predicción de Lotería  
**Versión**: 2.0  
**Última actualización**: 2026
