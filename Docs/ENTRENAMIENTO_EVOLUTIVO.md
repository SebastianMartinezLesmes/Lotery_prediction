# 🧬 Entrenamiento Evolutivo

## Descripción

Sistema avanzado de entrenamiento que mantiene múltiples variantes de modelos que compiten y evolucionan continuamente, mejorando automáticamente sin reiniciar el proceso.

---

## 🎯 Concepto

### Estrategia de 3 Variantes

1. **Variante #1 (PRODUCTION)** 🏆
   - El mejor modelo actual
   - Usado para predicciones en producción
   - Guardado en `IA_models/modelo_*.pkl`

2. **Variante #2 (EXPERIMENTAL_1)** 🧪
   - Explora configuraciones alternativas
   - Compite con producción
   - Si supera a producción, se intercambian roles

3. **Variante #3 (EXPERIMENTAL_2)** 🧪
   - Explora configuraciones alternativas
   - Compite con producción
   - Si supera a producción, se intercambian roles

### Evolución Continua

```
Iteración 1-100:
  Prod: 0.65 | Exp1: 0.60 | Exp2: 0.58
  → Prod sigue siendo el mejor

Iteración 101-200:
  Prod: 0.65 | Exp1: 0.68 | Exp2: 0.62
  → Exp1 supera a Prod
  → 🔄 PROMOCIÓN: Exp1 → Prod, Prod → Exp1

Iteración 201-300:
  Prod: 0.68 | Exp1: 0.65 | Exp2: 0.70
  → Exp2 supera a Prod
  → 🔄 PROMOCIÓN: Exp2 → Prod, Prod → Exp2

... continúa evolucionando sin reiniciar
```

---

## ✨ Características

- **Evolución automática**: Las variantes compiten y el mejor siempre está en producción
- **Sin reinicio**: El proceso continúa desde donde quedó
- **Mutación inteligente**: Variantes sin mejora mutan para explorar nuevas configuraciones
- **Early stopping**: Detiene si no hay mejora global
- **Persistencia**: Estado guardado en JSON
- **Logging completo**: Registro de todas las promociones y mutaciones

---

## 🚀 Uso

### Entrenamiento Básico

```bash
# Entrenar todas las loterías
python scripts/train_evolutionary.py

# Entrenar lotería específica
python scripts/train_evolutionary.py --lottery "ASTRO LUNA"
```

### Entrenamiento Avanzado

```bash
# Con más iteraciones
python scripts/train_evolutionary.py --iterations 20000

# Con más patience
python scripts/train_evolutionary.py --patience 200

# Combinado
python scripts/train_evolutionary.py --lottery "ASTRO SOL" --iterations 15000 --patience 150
```

### Ver Estado de Variantes

```bash
# Ver todas las variantes
python scripts/train_evolutionary.py --status

# Ver variantes de lotería específica
python scripts/train_evolutionary.py --status --lottery "ASTRO LUNA"
```

---

## 📊 Salida del Entrenamiento

### Durante el Entrenamiento

```
** 450/10000 (4.5%) | Prod: Acc=0.6523 F1=0.6234 | Best: 0.6379 | No-improve: 12
```

- `**`: Indica que hubo mejora en esta iteración
- `450/10000`: Iteración actual / total
- `Prod`: Métricas del modelo en producción
- `Best`: Mejor score combinado alcanzado
- `No-improve`: Iteraciones sin mejora (para early stopping)

### Promoción de Variante

```
🔄 PROMOCIÓN: Variante 2 (acc=0.6800) supera a producción (acc=0.6500)
✅ Nueva producción: Variante 2
```

### Mutación de Variante

```
Mutando variante 3 (sin mejora en 200 iter)
Mutación creada para variante 3: n_est=250, depth=5, split=3
```

### Resumen Final

```
======================================================================
VARIANTES - ASTRO LUNA (result)
======================================================================

🏆 Variante #2 (PRODUCTION)
   Accuracy: 0.6800
   F1-Score: 0.6543
   Combined: 0.6672
   Config: n_est=150, depth=6, split=3
   Iteraciones: 1250
   Última mejora: iter 1180

🧪 Variante #1 (EXPERIMENTAL_1)
   Accuracy: 0.6500
   F1-Score: 0.6234
   Combined: 0.6367
   Config: n_est=200, depth=4, split=5
   Iteraciones: 1250
   Última mejora: iter 890

🧪 Variante #3 (EXPERIMENTAL_2)
   Accuracy: 0.6420
   F1-Score: 0.6189
   Combined: 0.6305
   Config: n_est=250, depth=5, split=3
   Iteraciones: 1250
   Última mejora: iter 1050
======================================================================
```

---

## 🔧 Configuración de Variantes

### Hiperparámetros Explorados

Cada variante explora diferentes combinaciones:

```python
n_estimators: [100, 150, 200, 250, 300]
max_depth: [3, 4, 5, 6, 7, 8]
min_samples_split: [2, 3, 5, 7, 10]
```

### Configuraciones Iniciales

**Variante #1 (PRODUCTION):**
- n_estimators: 200
- max_depth: 4
- min_samples_split: 5
- Configuración balanceada

**Variante #2 (EXPERIMENTAL_1):**
- n_estimators: 150
- max_depth: 6
- min_samples_split: 3
- Más profundidad, menos árboles

**Variante #3 (EXPERIMENTAL_2):**
- n_estimators: 250
- max_depth: 3
- min_samples_split: 7
- Más árboles, menos profundidad

---

## 📁 Archivos Generados

### Variantes JSON

```
IA_models/variants_astro_luna_result.json
IA_models/variants_astro_luna_series.json
IA_models/variants_astro_sol_result.json
IA_models/variants_astro_sol_series.json
```

**Formato:**
```json
[
  {
    "id": 1,
    "role": "EXPERIMENTAL_1",
    "accuracy": 0.6500,
    "f1_score": 0.6234,
    "n_estimators": 200,
    "max_depth": 4,
    "min_samples_split": 5,
    "random_state": 42,
    "iterations_trained": 1250,
    "last_improvement": 890,
    "created_at": "2026-02-27T14:30:00"
  },
  {
    "id": 2,
    "role": "PRODUCTION",
    "accuracy": 0.6800,
    "f1_score": 0.6543,
    ...
  }
]
```

### Modelos PKL

Solo el modelo en PRODUCTION se guarda en el archivo principal:

```
IA_models/modelo_result_astro_luna.pkl  ← Variante en PRODUCTION
IA_models/modelo_series_astro_luna.pkl  ← Variante en PRODUCTION
```

---

## 🔄 Flujo de Evolución

### 1. Inicialización

```python
# Primera ejecución: crea 3 variantes con configs diferentes
Variante #1: PRODUCTION (config A)
Variante #2: EXPERIMENTAL_1 (config B)
Variante #3: EXPERIMENTAL_2 (config C)
```

### 2. Entrenamiento Iterativo

```python
for iteration in range(max_iterations):
    # Entrenar todas las variantes
    for variant in variants:
        train(variant)
        evaluate(variant)
    
    # Verificar si experimental supera a production
    if experimental.score > production.score:
        promote(experimental)  # Intercambiar roles
```

### 3. Mutación Automática

```python
# Cada 200 iteraciones
if variant.iterations_since_improvement > 200:
    mutate(variant)  # Nuevos hiperparámetros
```

### 4. Early Stopping

```python
if global_iterations_without_improvement > patience:
    stop()  # Detener entrenamiento
```

### 5. Continuación

```python
# Próxima ejecución: carga estado y continúa
load_variants()  # Desde JSON
continue_training()  # Sin reiniciar
```

---

## 🎯 Ventajas vs Entrenamiento Tradicional

| Característica | Tradicional | Evolutivo |
|----------------|-------------|-----------|
| Variantes | 1 modelo | 3 modelos compitiendo |
| Exploración | Fija | Continua con mutaciones |
| Mejora | Manual | Automática |
| Reinicio | Desde cero | Continúa desde estado |
| Adaptación | No | Sí, evoluciona |
| Producción | Puede degradarse | Siempre el mejor |

---

## 📈 Casos de Uso

### 1. Mejora Continua

```bash
# Día 1: Entrenar inicial
python scripts/train_evolutionary.py --iterations 5000

# Día 2: Continuar mejorando (sin reiniciar)
python scripts/train_evolutionary.py --iterations 5000

# Día 3: Más mejoras
python scripts/train_evolutionary.py --iterations 5000

# El modelo evoluciona continuamente
```

### 2. Experimentación Automática

```bash
# El sistema explora automáticamente diferentes configuraciones
# Sin necesidad de GridSearch manual
python scripts/train_evolutionary.py --iterations 20000
```

### 3. Mantenimiento Programado

```bash
# En scheduler: entrenar evolutivamente cada semana
# El modelo se adapta a nuevos datos automáticamente
```

### 4. Comparación de Variantes

```bash
# Ver qué configuraciones funcionan mejor
python scripts/train_evolutionary.py --status
```

---

## 🔍 Monitoreo

### Logs

Todos los eventos se registran en `logs/evolutionary.log`:

```
2026-02-27 14:30:00 - evolutionary_training - INFO - EvolutionaryTrainer inicializado
2026-02-27 14:35:12 - evolutionary_training - INFO - 🔄 PROMOCIÓN: Variante 2 supera a producción
2026-02-27 14:40:30 - evolutionary_training - INFO - Mutando variante 3 (sin mejora en 200 iter)
2026-02-27 14:45:00 - evolutionary_training - INFO - Entrenamiento evolutivo completado
```

### Métricas

```bash
# Ver estado actual
python scripts/train_evolutionary.py --status

# Ver logs
tail -f logs/evolutionary.log
```

---

## 🚨 Troubleshooting

### Problema: Variantes no mejoran

```bash
# Aumentar iteraciones
python scripts/train_evolutionary.py --iterations 20000

# Reducir patience para más mutaciones
python scripts/train_evolutionary.py --patience 50
```

### Problema: Archivo de variantes corrupto

```bash
# Eliminar y reiniciar
rm IA_models/variants_*.json
python scripts/train_evolutionary.py
```

### Problema: Memoria insuficiente

```bash
# Reducir n_estimators en el código
# O entrenar una lotería a la vez
python scripts/train_evolutionary.py --lottery "ASTRO LUNA"
```

---

## 🔬 Detalles Técnicos

### Algoritmo de Promoción

```python
def promote_variant(experimental_id):
    production = get_production_variant()
    experimental = get_variant(experimental_id)
    
    # Intercambiar roles
    production.role, experimental.role = experimental.role, production.role
    
    # Guardar nuevo modelo de producción
    save_model(experimental)
```

### Algoritmo de Mutación

```python
def mutate_variant(variant):
    return ModelVariant(
        n_estimators=random.choice([100, 150, 200, 250, 300]),
        max_depth=random.choice([3, 4, 5, 6, 7, 8]),
        min_samples_split=random.choice([2, 3, 5, 7, 10]),
        random_state=random.randint(0, 10000)
    )
```

### Score Combinado

```python
combined_score = (accuracy + f1_score) / 2
```

---

## 📚 Mejores Prácticas

1. **Iteraciones suficientes**: Mínimo 5000 para ver evolución
2. **Patience adecuado**: 100-200 para balance exploración/explotación
3. **Monitoreo regular**: Revisar estado de variantes periódicamente
4. **Continuación**: No reiniciar, dejar que evolucione
5. **Backup**: Respaldar archivos de variantes antes de cambios grandes

---

## 🔄 Integración con Sistema Existente

### Usar en lugar de entrenamiento tradicional

```bash
# Antes
python main.py --train

# Ahora
python scripts/train_evolutionary.py
```

### Usar en scheduler

```python
# En scripts/scheduler.py
def ejecutar_entrenamiento_evolutivo():
    subprocess.run([
        sys.executable,
        "scripts/train_evolutionary.py",
        "--iterations", "10000"
    ])
```

---

## 📖 Referencias

- [Evolutionary Algorithms](https://en.wikipedia.org/wiki/Evolutionary_algorithm)
- [Genetic Programming](https://en.wikipedia.org/wiki/Genetic_programming)
- [AutoML](https://www.automl.org/)

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Estado:** ✅ Experimental → Producción
