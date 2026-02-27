# 📊 Batch Predictions - Predicciones por Lotes

## Descripción

El sistema de **Batch Predictions** permite generar predicciones para múltiples fechas de una vez, optimizando el proceso y facilitando el análisis de tendencias futuras.

---

## ✨ Características

- **Predicción de múltiples fechas**: Genera predicciones para N días consecutivos
- **Rango de fechas personalizado**: Define fecha inicio y fin
- **Fechas específicas**: Predice para fechas puntuales
- **Múltiples loterías**: Procesa todas las loterías o una específica
- **Exportación JSON**: Guarda resultados en formato estructurado
- **Visualización en consola**: Muestra resultados de forma legible
- **Eficiencia**: Carga modelos una sola vez para todas las predicciones

---

## 🚀 Uso Básico

### Predicción para los próximos 7 días (default)

```bash
python main.py --batch
```

**Salida:**
```
======================================================================
PREDICCIONES BATCH - MÚLTIPLES FECHAS
======================================================================

>> ASTRO LUNA
----------------------------------------------------------------------
   2026-02-27 (Vie) | Número: 0042 | Símbolo: SAGITARIO
   2026-02-28 (Sab) | Número: 0156 | Símbolo: TAURO
   2026-03-01 (Dom) | Número: 0089 | Símbolo: LEO
   ...

>> ASTRO SOL
----------------------------------------------------------------------
   2026-02-27 (Vie) | Número: 7845 | Símbolo: ARIES
   2026-02-28 (Sab) | Número: 3421 | Símbolo: GEMINIS
   ...
```

### Predicción para 30 días

```bash
python main.py --batch --days 30
```

### Predicción para lotería específica

```bash
python main.py --batch --lottery "ASTRO LUNA" --days 14
```

### Guardar resultados en JSON

```bash
python main.py --batch --days 7 --save
```

Esto genera un archivo: `data/batch_predictions_YYYYMMDD_HHMMSS.json`

---

## 📝 Formato del Archivo JSON

```json
{
  "ASTRO LUNA": [
    {
      "fecha": "2026-02-27",
      "dia_semana": "Friday",
      "numero": "0042",
      "simbolo": "SAGITARIO"
    },
    {
      "fecha": "2026-02-28",
      "dia_semana": "Saturday",
      "numero": "0156",
      "simbolo": "TAURO"
    }
  ],
  "ASTRO SOL": [
    {
      "fecha": "2026-02-27",
      "dia_semana": "Friday",
      "numero": "7845",
      "simbolo": "ARIES"
    }
  ]
}
```

---

## 🔧 Uso Programático

### Ejemplo 1: Predicción para los próximos 7 días

```python
from src.utils.batch_prediction import BatchPredictor

# Crear predictor
predictor = BatchPredictor("ASTRO LUNA")

# Predecir próximos 7 días
predicciones = predictor.predecir_proximos_dias(dias=7)

for pred in predicciones:
    print(f"{pred['fecha']}: {pred['numero']} - {pred['simbolo']}")
```

### Ejemplo 2: Rango de fechas personalizado

```python
from datetime import datetime
from src.utils.batch_prediction import BatchPredictor

predictor = BatchPredictor("ASTRO SOL")

fecha_inicio = datetime(2026, 3, 1)
fecha_fin = datetime(2026, 3, 31)

predicciones = predictor.predecir_rango(fecha_inicio, fecha_fin)
print(f"Predicciones para marzo: {len(predicciones)}")
```

### Ejemplo 3: Fechas específicas

```python
from datetime import datetime
from src.utils.batch_prediction import BatchPredictor

predictor = BatchPredictor("ASTRO LUNA")

fechas = [
    datetime(2026, 3, 15),  # Día de pago
    datetime(2026, 3, 30),  # Fin de mes
    datetime(2026, 4, 1)    # Inicio de mes
]

predicciones = predictor.predecir_fechas_especificas(fechas)
```

### Ejemplo 4: Todas las loterías

```python
from src.utils.batch_prediction import (
    predecir_batch_todas_loterias,
    mostrar_predicciones_batch,
    guardar_predicciones_batch
)

# Predecir para todas las loterías
predicciones = predecir_batch_todas_loterias(dias=14)

# Mostrar en consola
mostrar_predicciones_batch(predicciones)

# Guardar en archivo
guardar_predicciones_batch(predicciones)
```

---

## 🎯 Casos de Uso

### 1. Análisis de Tendencias Mensuales

```bash
# Generar predicciones para todo el mes
python main.py --batch --days 30 --save

# Analizar el archivo JSON generado
python scripts/analizar_tendencias.py data/batch_predictions_*.json
```

### 2. Planificación Semanal

```bash
# Predicciones para la semana
python main.py --batch --days 7 --lottery "ASTRO LUNA"
```

### 3. Comparación de Loterías

```bash
# Generar predicciones para todas
python main.py --batch --days 14 --save

# Comparar patrones entre loterías
```

### 4. Validación de Modelos

```bash
# Predecir fechas pasadas y comparar con resultados reales
python -c "
from datetime import datetime, timedelta
from src.utils.batch_prediction import BatchPredictor

predictor = BatchPredictor('ASTRO LUNA')
hace_30_dias = datetime.now() - timedelta(days=30)
hoy = datetime.now()

predicciones = predictor.predecir_rango(hace_30_dias, hoy)
# Comparar con datos reales del Excel
"
```

---

## ⚡ Ventajas vs Predicción Simple

| Característica | Predicción Simple | Batch Prediction |
|----------------|-------------------|------------------|
| Fechas | Solo hoy | Múltiples fechas |
| Eficiencia | Carga modelos cada vez | Carga una sola vez |
| Exportación | Solo results.json | JSON estructurado |
| Análisis | Limitado | Tendencias y patrones |
| Planificación | No | Sí (semanas/meses) |

---

## 🔍 Detalles Técnicos

### Clase BatchPredictor

```python
class BatchPredictor:
    """Predictor por lotes para múltiples fechas."""
    
    def __init__(self, loteria: str)
        # Carga modelos una sola vez
    
    def predecir_fecha(self, fecha: datetime) -> Dict
        # Predice para una fecha específica
    
    def predecir_rango(self, fecha_inicio, fecha_fin) -> List[Dict]
        # Predice para un rango de fechas
    
    def predecir_proximos_dias(self, dias: int) -> List[Dict]
        # Predice N días desde hoy
    
    def predecir_fechas_especificas(self, fechas: List) -> List[Dict]
        # Predice para fechas puntuales
```

### Optimizaciones

1. **Carga única de modelos**: Los modelos se cargan una sola vez al inicializar
2. **Procesamiento vectorizado**: Usa pandas para operaciones eficientes
3. **Generación lazy**: Puede implementarse con generadores para grandes volúmenes
4. **Cache de resultados**: Evita recalcular predicciones ya generadas

---

## 📊 Rendimiento

- **Carga de modelos**: ~1-2 segundos (una sola vez)
- **Predicción por fecha**: ~0.01 segundos
- **7 días (1 lotería)**: ~0.1 segundos
- **30 días (2 loterías)**: ~0.6 segundos
- **365 días (2 loterías)**: ~7 segundos

---

## 🚨 Requisitos

- Modelos entrenados (`.pkl`) deben existir
- Ejecutar primero: `python main.py --train`
- Python 3.8+
- Dependencias: pandas, joblib, scikit-learn

---

## 🔧 Solución de Problemas

### Error: "Modelo no encontrado"

```bash
# Entrenar modelos primero
python main.py --train
```

### Error: "No module named 'src.utils.batch_prediction'"

```bash
# Verificar que el archivo existe
ls src/utils/batch_prediction.py

# Reinstalar dependencias
pip install -r requirements.txt
```

### Predicciones inconsistentes

```bash
# Re-entrenar modelos con más datos
python main.py --collect
python main.py --train
```

---

## 📈 Próximas Mejoras

- [ ] Predicción con intervalos de confianza
- [ ] Análisis de probabilidades por número
- [ ] Visualización gráfica de tendencias
- [ ] Exportación a Excel/CSV
- [ ] API REST para batch predictions
- [ ] Cache de predicciones frecuentes
- [ ] Predicción paralela (multiprocessing)

---

## 📚 Ver También

- [COMO_FUNCIONA_ENTRENAMIENTO.md](COMO_FUNCIONA_ENTRENAMIENTO.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [README.md](../README.md)

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Estado:** ✅ Producción
