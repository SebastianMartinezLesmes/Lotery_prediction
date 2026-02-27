# 📊 Comparación de Sistemas de Entrenamiento

## Resumen

El sistema ofrece **3 modos de entrenamiento** con diferentes características y casos de uso.

---

## 🎯 Los 3 Sistemas

### 1. Entrenamiento Básico
**Comando:** `python main.py --train`

**Características:**
- RandomForest con configuración fija
- Early stopping básico
- Sistema Top 3 entrenamientos
- Rápido y simple

**Ventajas:**
- ✓ Muy rápido
- ✓ Fácil de usar
- ✓ Bajo consumo de recursos

**Desventajas:**
- ✗ Un solo algoritmo
- ✗ Sin exploración automática
- ✗ Features básicos

### 2. Entrenamiento Avanzado
**Comando:** `python scripts/train_advanced.py`

**Características:**
- Múltiples algoritmos: RF, XGBoost, LightGBM
- Feature engineering avanzado (40+ features)
- GridSearch/RandomizedSearch
- Validación cruzada estratificada

**Ventajas:**
- ✓ Máxima precisión
- ✓ Exploración exhaustiva
- ✓ Features avanzados

**Desventajas:**
- ✗ Lento (horas)
- ✗ Alto consumo de recursos
- ✗ No evoluciona automáticamente

### 3. Entrenamiento Híbrido 🆕🔥
**Comando:** `python scripts/train_hybrid.py`

**Características:**
- 3 algoritmos compitiendo: RF, XGBoost, LightGBM
- Feature engineering avanzado (40+ features)
- Evolución continua sin reiniciar
- Mutación automática
- El mejor siempre en producción

**Ventajas:**
- ✓ Lo mejor de ambos mundos
- ✓ Evolución automática
- ✓ Sin reinicio
- ✓ Adaptativo

**Desventajas:**
- ✗ Más complejo
- ✗ Requiere más recursos que básico

---

## 📊 Tabla Comparativa

| Característica | Básico | Avanzado | Híbrido 🔥 |
|----------------|--------|----------|-----------|
| **Algoritmos** | 1 (RF) | 3 (RF, XGB, LGB) | 3 compitiendo |
| **Features** | 4 básicos | 40+ avanzados | 40+ avanzados |
| **Evolución** | No | No | Sí, continua |
| **Exploración** | Fija | Exhaustiva | Automática |
| **Velocidad** | ⚡⚡⚡ Muy rápido | 🐌 Lento | ⚡⚡ Rápido |
| **Precisión** | ⭐⭐ Media | ⭐⭐⭐ Alta | ⭐⭐⭐ Alta |
| **Recursos** | 💻 Bajo | 💻💻💻 Alto | 💻💻 Medio |
| **Adaptación** | ✗ No | ✗ No | ✓ Sí |
| **Reinicio** | Desde cero | Desde cero | Continúa |
| **Mejor para** | Desarrollo | Exploración inicial | Producción |

---

## 🎯 ¿Cuál Usar?

### Escenario 1: Desarrollo Rápido
```bash
python main.py --train
```
**Cuándo:** Pruebas rápidas, desarrollo, prototipos

### Escenario 2: Exploración Inicial
```bash
python scripts/train_advanced.py --algorithm auto
```
**Cuándo:** Primera vez, quieres saber qué algoritmo funciona mejor

### Escenario 3: Producción (Recomendado) 🔥
```bash
python scripts/train_hybrid.py
```
**Cuándo:** Producción, mejora continua, máximo rendimiento

---

## 🚀 Estrategia Recomendada

### Fase 1: Exploración (Una vez)
```bash
# Descubre el mejor algoritmo
python scripts/train_advanced.py --algorithm auto
```
**Resultado:** Sabes si RF, XGBoost o LightGBM funciona mejor

### Fase 2: Producción (Continuo)
```bash
# Usa híbrido para evolución continua
python scripts/train_hybrid.py
```
**Resultado:** Los 3 algoritmos compiten y evolucionan automáticamente

### Fase 3: Mantenimiento (Programado)
```bash
# En scheduler: ejecutar híbrido semanalmente
# El sistema se adapta automáticamente a nuevos datos
```

---

## 📈 Ejemplo de Evolución

### Semana 1: Exploración Inicial
```bash
python scripts/train_advanced.py --algorithm auto
```
**Resultado:**
- RandomForest: 0.65
- XGBoost: 0.68 ← Mejor
- LightGBM: 0.66

### Semana 2-4: Evolución Híbrida
```bash
python scripts/train_hybrid.py --iterations 10000
```
**Resultado:**
- Variante #1 (RF): 0.67
- Variante #2 (XGB): 0.70 ← Producción
- Variante #3 (LGB): 0.68

### Semana 5-8: Continúa Evolucionando
```bash
python scripts/train_hybrid.py --iterations 10000
```
**Resultado:**
- Variante #1 (RF): 0.69
- Variante #2 (XGB): 0.71
- Variante #3 (LGB): 0.72 ← Nueva producción

**El sistema mejora automáticamente sin intervención manual**

---

## 🔧 Configuración por Sistema

### Básico
```env
ITERATIONS=8000
MIN_ACCURACY=0.7
```

### Avanzado
```env
USE_ADVANCED_ML=true
ML_ALGORITHM=auto
HYPERPARAMETER_SEARCH=random
SEARCH_ITERATIONS=20
CV_FOLDS=5
ENABLE_FEATURE_ENGINEERING=true
```

### Híbrido
```bash
# Configuración en línea de comandos
python scripts/train_hybrid.py \
  --iterations 10000 \
  --patience 100
```

---

## 💡 Casos de Uso Específicos

### Caso 1: Prototipo Rápido
**Sistema:** Básico  
**Razón:** Necesitas resultados en minutos

```bash
python main.py --train
```

### Caso 2: Investigación
**Sistema:** Avanzado  
**Razón:** Quieres explorar todas las opciones

```bash
python scripts/train_advanced.py --algorithm auto
```

### Caso 3: Producción
**Sistema:** Híbrido  
**Razón:** Necesitas el mejor rendimiento continuo

```bash
python scripts/train_hybrid.py
```

### Caso 4: Recursos Limitados
**Sistema:** Básico o Híbrido sin features  
**Razón:** Computadora con poca RAM

```bash
python scripts/train_hybrid.py --no-features
```

### Caso 5: Máxima Precisión
**Sistema:** Híbrido con features  
**Razón:** Precisión es más importante que velocidad

```bash
python scripts/train_hybrid.py --iterations 20000
```

---

## 📊 Benchmarks

### Tiempo de Ejecución (1 lotería)

| Sistema | Tiempo | Iteraciones |
|---------|--------|-------------|
| Básico | 5-10 min | 8000 |
| Avanzado | 2-4 horas | GridSearch |
| Híbrido | 15-30 min | 10000 |

### Uso de Memoria

| Sistema | RAM |
|---------|-----|
| Básico | ~500 MB |
| Avanzado | ~2 GB |
| Híbrido | ~1 GB |

### Precisión Típica

| Sistema | Accuracy |
|---------|----------|
| Básico | 0.60-0.65 |
| Avanzado | 0.65-0.72 |
| Híbrido | 0.68-0.75 |

---

## 🔄 Migración Entre Sistemas

### De Básico a Híbrido
```bash
# Los modelos .pkl son compatibles
# Solo ejecuta híbrido
python scripts/train_hybrid.py
```

### De Avanzado a Híbrido
```bash
# Híbrido usa los mismos algoritmos
# Pero con evolución continua
python scripts/train_hybrid.py
```

### Usar Múltiples Sistemas
```bash
# Puedes usar diferentes sistemas para diferentes loterías
python main.py --train --lottery "ASTRO LUNA"  # Básico
python scripts/train_hybrid.py --lottery "ASTRO SOL"  # Híbrido
```

---

## 🎓 Recomendaciones Finales

### Para Principiantes
1. Empieza con **Básico** para familiarizarte
2. Prueba **Avanzado** para ver qué algoritmo funciona mejor
3. Migra a **Híbrido** para producción

### Para Expertos
1. Usa **Híbrido** directamente
2. Ajusta hiperparámetros según necesidad
3. Monitorea evolución con `--status`

### Para Producción
1. **Híbrido** es la mejor opción
2. Programa ejecuciones semanales
3. Monitorea con sistema de alertas

---

## 📚 Ver También

- [ENTRENAMIENTO_EVOLUTIVO.md](ENTRENAMIENTO_EVOLUTIVO.md)
- [COMO_FUNCIONA_ENTRENAMIENTO.md](COMO_FUNCIONA_ENTRENAMIENTO.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Versión:** 2.0  
**Fecha:** Febrero 2026  
**Recomendación:** 🔥 Híbrido para producción
