# 🎰 Sistema de Predicción de Lotería

Sistema automatizado desarrollado en Python para predicción de resultados de lotería mediante Machine Learning con arquitectura moderna y modular.

## ✨ Características Principales

- 🤖 Machine Learning con RandomForest optimizado
- 📊 Visualización en tiempo real del entrenamiento
- ⚙️ Configuración centralizada con soporte para múltiples entornos
- 🔄 Entrenamiento iterativo con búsqueda de mejores modelos
- 📈 Dos modelos independientes por lotería (números y símbolos)
- 🗂️ Gestión automática de modelos en formato `.pkl`
- 📝 Sistema de logging robusto y estructurado
- ✅ Validación de datos con Pydantic
- 🧹 Limpieza automática de caché

---

## 📁 Estructura del Proyecto

```
Lotery_prediction/
├── .env                          # Configuración local
├── .env.example                  # Plantilla de configuración
├── .gitignore                    # Control de versiones
├── index.py                      # Punto de entrada principal
├── main.py                       # CLI avanzado
├── requirements.txt              # Dependencias
├── LICENSE                       # Licencia
├── README.md                     # Documentación
│
├── data/                         # Datos generados
│   ├── .gitkeep
│   ├── results.json              # Predicciones
│   └── resultados_astro.xlsx     # Datos de lotería
│
├── Docs/                         # Documentación técnica
│   ├── ARCHITECTURE.md
│   ├── COMO_FUNCIONA_ENTRENAMIENTO.md
│   ├── ESTRATEGIA_TOP3_MODELOS.md
│   ├── GESTION_LOGS_ENTRENAMIENTO.md
│   └── LIMPIEZA_COMPLETADA.md
│
├── IA_models/                    # Modelos entrenados
│   ├── .gitkeep
│   ├── modelo_result_astro_luna.pkl
│   ├── modelo_result_astro_sol.pkl
│   ├── modelo_series_astro_luna.pkl
│   └── modelo_series_astro_sol.pkl
│
├── logs/                         # Logs del sistema
│   ├── .gitkeep
│   ├── dependencias.log
│   ├── log_loteria.log
│   ├── tiempos.log
│   └── training_*.json
│
├── scripts/                      # Scripts de utilidad
│   ├── setup_entorno.py          # Configuración inicial
│   ├── verificar_ia_models.py    # Verificación de modelos
│   └── visualizar_entrenamiento.py  # Análisis de entrenamientos
│
├── src/                          # Código fuente
│   ├── api/
│   │   ├── client.py            # Cliente HTTP mejorado
│   │   └── __init__.py
│   │
│   ├── core/                    # Núcleo del sistema
│   │   ├── config.py            # Configuración centralizada
│   │   ├── exceptions.py        # Excepciones personalizadas
│   │   ├── logger.py            # Sistema de logging
│   │   ├── validators.py        # Validadores
│   │   └── __init__.py
│   │
│   ├── excel/                   # Manejo de Excel
│   │   ├── read_excel.py
│   │   └── __init__.py
│   │
│   ├── models/                  # Esquemas Pydantic
│   │   ├── schemas.py
│   │   └── __init__.py
│   │
│   └── utils/                   # Utilidades
│       ├── dependencies.py
│       ├── drop_cache.py
│       ├── prediction.py
│       ├── batch_prediction.py  # Predicciones por lotes 🆕
│       ├── result.py
│       ├── training.py
│       ├── training_visualizer.py
│       ├── zodiaco.py
│       └── __init__.py
│
└── task/
    └── task.md
```

---

## 🚀 Ejecución del Sistema

### Opción 1: Pipeline completo (recomendado)

```bash
python index.py
```

Este comando ejecuta el pipeline completo:
1. Instalación/verificación de dependencias
2. Recolección o actualización de datos desde Excel/API
3. Predicción de resultados usando modelos previamente entrenados
4. Limpieza de archivos de caché

### Opción 2: CLI con componentes individuales

```bash
# Ver configuración actual
python main.py --config

# Ejecutar pipeline completo
python main.py

# Solo verificar dependencias
python main.py --deps

# Solo recolectar datos
python main.py --collect

# Solo entrenar modelos (modo básico)
python main.py --train

# Solo generar predicciones
python main.py --predict

# Predicción para lotería específica
python main.py --predict --lottery ASTRO

# Predicciones por lotes (múltiples fechas) 🆕
python main.py --batch                    # 7 días (default)
python main.py --batch --days 30          # 30 días
python main.py --batch --save             # Guardar en JSON
python main.py --batch --lottery "ASTRO LUNA" --days 14

# Ver ayuda
python main.py --help
```

### Opción 3: Entrenamiento Avanzado 🆕

```bash
# Entrenamiento con ML avanzado (recomendado)
python scripts/train_advanced.py

# Con algoritmo específico
python scripts/train_advanced.py --algorithm XGBoost

# Modo AUTO (prueba todos los algoritmos)
python scripts/train_advanced.py --algorithm auto
```

### Opción 4: Entrenamiento Híbrido 🆕🔥

```bash
# Lo mejor de ambos mundos: múltiples algoritmos + evolución continua
python scripts/train_hybrid.py

# Ver estado de variantes
python scripts/train_hybrid.py --status

# Sin feature engineering (más rápido)
python scripts/train_hybrid.py --no-features
```

**Características del Híbrido:**
- 3 algoritmos compitiendo: RandomForest, XGBoost, LightGBM
- Feature engineering avanzado (40+ features)
- Evolución continua sin reiniciar
- El mejor algoritmo siempre en producción
python scripts/train_advanced.py --algorithm auto

# Con Grid Search (más preciso)
python scripts/train_advanced.py --search grid

# Personalizado
python scripts/train_advanced.py --algorithm auto --search grid --cv-folds 10
```

Ver [ML_AVANZADO.md](Docs/ML_AVANZADO.md) para más opciones.

### Opción 4: Entrenamiento directo de modelos (básico)

```bash
python -m src.utils.training
```

Esto buscará los modelos `.pkl` previamente creados por lotería. Si existen, los perfeccionará. Si no se encuentra ningún modelo previo, se mostrará un mensaje:  
**"Loterías no encontradas"**

---

## 🧠 Funcionamiento del Sistema de Machine Learning

El sistema ofrece dos modos de entrenamiento:

### Modo Básico (Legacy)
Flujo tradicional con RandomForest y features básicas.

### Modo Avanzado (Nuevo) 🆕
Sistema mejorado con:
- **Validación cruzada estratificada** con StratifiedKFold
- **Optimización de hiperparámetros** (GridSearchCV/RandomizedSearchCV)
- **Múltiples algoritmos** (RandomForest, XGBoost, LightGBM)
- **Feature engineering avanzado** (40+ features)
- **Métricas de negocio** (ROI, aciertos consecutivos, confianza)

Ver [ML_AVANZADO.md](Docs/ML_AVANZADO.md) para documentación completa.

El flujo general de predicción y entrenamiento incluye:

1. **Carga de Datos:**  
   Desde `resultados_*.xlsx`, usando `read_excel.py`.

2. **Preprocesamiento:**  
   Generación de secuencias n-gram para series y codificación para predicción de resultados.

3. **Entrenamiento de Modelos:**  
   Se crean dos modelos independientes por cada lotería:

   - `modelo_result_{loteria}.pkl`: para predecir el número y símbolo ganador.
   - `modelo_series_{loteria}.pkl`: para aprender secuencias históricas usando n-gramas.

4. **Evaluación:**  
   Se comparan modelos mediante validación cruzada y se guarda el mejor en la carpeta `IA_models/`.

5. **Predicción:**  
   Basada en patrones aprendidos para cada lotería de forma individual.

6. **Visualización:** 🆕  
   Progreso en tiempo real con barras de progreso, métricas y reportes guardados.

### 📊 Visualización de Entrenamiento

El sistema incluye visualización en tiempo real del progreso con métricas actualizadas:

```bash
# Entrenar con visualización en tiempo real
python main.py --train

# Ver entrenamientos guardados
python visualizar_entrenamiento.py --latest

# Ver con gráfico
python visualizar_entrenamiento.py --latest --graph

# Comparar entrenamientos
python visualizar_entrenamiento.py --compare
```

**Formato de visualización:**
```
** 65/8000 (0.8%) | Time: 1.8m/3.7h | Result: 0.0079 (0.0044) | Series: 0.0945 (0.0856) | Best: R=0.0157 S=0.1181 | Improvements: 5
```

- `**` indica mejora en el modelo actual
- Progreso: iteración actual / total (porcentaje)
- Time: tiempo transcurrido / tiempo estimado
- Result/Series: accuracy actual (F1-score)
- Best: mejores valores alcanzados
- Improvements: contador de mejoras

Ver [COMO_FUNCIONA_ENTRENAMIENTO.md](Docs/COMO_FUNCIONA_ENTRENAMIENTO.md) para más detalles.

### 📊 Predicciones por Lotes (Batch Predictions) 🆕

El sistema permite generar predicciones para múltiples fechas de una vez:

```bash
# Predicción para los próximos 7 días
python main.py --batch

# Predicción para 30 días
python main.py --batch --days 30

# Guardar resultados en JSON
python main.py --batch --days 14 --save

# Lotería específica
python main.py --batch --lottery "ASTRO LUNA" --days 7
```

**Salida de ejemplo:**
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
```

**Ventajas:**
- Genera predicciones para múltiples fechas en una sola ejecución
- Exporta resultados en formato JSON estructurado
- Ideal para análisis de tendencias y planificación
- Más eficiente que ejecutar predicciones individuales

Ver [BATCH_PREDICTIONS.md](Docs/BATCH_PREDICTIONS.md) para más detalles y ejemplos avanzados.

### 🚨 Sistema de Alertas 🆕

El sistema monitorea automáticamente el rendimiento de los modelos y notifica cuando las métricas caen bajo umbrales configurados:

**Configuración en `.env`:**
```env
ALERT_ACCURACY_WARNING=0.6
ALERT_ACCURACY_CRITICAL=0.5
ALERT_F1_WARNING=0.55
ALERT_F1_CRITICAL=0.45
```

**Uso:**
```bash
# Las alertas se generan automáticamente durante el entrenamiento
python main.py --train

# Ver alertas recientes
python scripts/ver_alertas.py

# Ver solo alertas críticas
python scripts/ver_alertas.py --level CRITICAL

# Generar reporte
python scripts/ver_alertas.py --report
```

**Ejemplo de alerta:**
```
======================================================================
!! ALERTA: Accuracy Bajo en ASTRO LUNA
======================================================================
Lotería: ASTRO LUNA
Métrica: accuracy_result
Valor actual: 0.5800
Umbral: 0.6000
Mensaje: El modelo result tiene un accuracy bajo. Considere re-entrenar.
======================================================================
```

**Características:**
- Monitoreo automático de accuracy y F1-score
- Múltiples niveles: INFO, WARNING, CRITICAL
- Notificaciones por consola, archivo y email (opcional)
- Historial completo en `logs/alerts.json`
- Reportes estadísticos y filtros avanzados

Ver [SISTEMA_ALERTAS.md](Docs/SISTEMA_ALERTAS.md) para configuración completa y uso avanzado.

---

## 📊 Datos de Entrada

Los datos provienen de archivos como:

```
data/resultados_astro.xlsx
```

El sistema los crea automáticamente si no existen, usando fuentes disponibles.

---

## 📋 Registro de Logs

Todos los eventos se registran automáticamente:

- `logs/log_loteria.log` — eventos del sistema principal
- `logs/dependencias.log` — instalación de paquetes
- `logs/tiempos.log` — tiempos de ejecución
- `logs/training_*.json` — historial detallado de entrenamientos
- `logs/training.log` — logs de entrenamiento
- `logs/api.log` — operaciones de API
- `logs/prediction.log` — logs de predicciones

---

## 🧹 Limpieza de Caché

Automática al final del flujo completo. También puedes ejecutarla manualmente:

```bash
python -m src.utils.drop_cache
```

---

## 📦 Dependencias

Las dependencias necesarias se cargan automáticamente desde:

```
src/utils/dependencies.py
```

---

## ⚙️ Orden de Ejecución de Scripts

Puedes modificar la ejecución del sistema en `index.py`:

```python
scripts = [
    ("Dependencias", "src/utils/dependencies.py"),
    ("Recolección de Datos", "src/excel/read_excel.py"),
    ("Predicción", "src/utils/prediction.py")
]
```

---

## ✅ Requisitos

- Python 3.8+
- pip

### Instalación de dependencias:

```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# O ejecutar el sistema (instala automáticamente)
python index.py
```

### Configuración:

1. Copiar el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Editar `.env` con tus valores:
```env
# API Configuration
API_URL=https://api-resultadosloterias.com/api/results/
FECHA_DEFECTO=2023-02-01

# Lottery Configuration
FIND_LOTERY=ASTRO

# Model Training
ITERATIONS=8000
MIN_ACCURACY=0.7
MAX_TRAINING_LOGS=3  # Número de archivos de entrenamiento a mantener por lotería

# Directories
MODELS_DIR=IA_models
DATA_DIR=data
LOGS_DIR=logs

# Logging
LOG_LEVEL=INFO
```

3. Ver configuración actual:
```bash
python main.py --config
```

---

## 🐳 Docker Deployment 🆕

### Inicio Rápido con Docker

```bash
# Construir imagen
docker build -t lottery-prediction:latest .

# Ejecutar con Docker Compose
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### Comandos Docker Útiles

```bash
# Pipeline completo
docker-compose run --rm lottery-system python main.py

# Solo entrenamiento
docker-compose run --rm lottery-system python main.py --train

# Batch predictions
docker-compose run --rm lottery-system python main.py --batch --days 30

# Scheduler automático
docker-compose up -d lottery-scheduler
```

Ver [DOCKER_DEPLOYMENT.md](Docs/DOCKER_DEPLOYMENT.md) para guía completa.

---

## ⏰ Entrenamientos Automáticos 🆕

### Scheduler Integrado

El sistema incluye un scheduler para ejecutar tareas automáticamente:

```bash
# Scheduler simple
python scripts/scheduler.py --mode simple

# Scheduler avanzado (APScheduler)
python scripts/scheduler.py --mode apscheduler

# Generar crontab para Linux/Mac
python scripts/scheduler.py --mode crontab
```

### Configuración en `.env`

```env
# Expresiones cron (minuto hora dia mes dia_semana)
SCHEDULE_COLLECT_CRON="0 8 * * *"      # Diario 8:00 AM
SCHEDULE_TRAIN_CRON="0 2 * * 0"        # Domingos 2:00 AM
SCHEDULE_PIPELINE_CRON="0 3 1 * *"     # Mensual día 1, 3:00 AM
```

### Tareas Programadas

- **Recolección diaria**: Actualiza datos cada mañana
- **Entrenamiento semanal**: Re-entrena modelos los domingos
- **Pipeline mensual**: Mantenimiento completo mensual

Ver [SCHEDULER.md](Docs/SCHEDULER.md) para configuración avanzada.

---

## 📚 Documentación Adicional

- [ARCHITECTURE.md](Docs/ARCHITECTURE.md) — Arquitectura del sistema
- [COMO_FUNCIONA_ENTRENAMIENTO.md](Docs/COMO_FUNCIONA_ENTRENAMIENTO.md) — Detalles del entrenamiento
- [BATCH_PREDICTIONS.md](Docs/BATCH_PREDICTIONS.md) — Predicciones por lotes
- [SISTEMA_ALERTAS.md](Docs/SISTEMA_ALERTAS.md) — Sistema de alertas y monitoreo
- [DOCKER_DEPLOYMENT.md](Docs/DOCKER_DEPLOYMENT.md) — Deployment con Docker 🆕
- [SCHEDULER.md](Docs/SCHEDULER.md) — Entrenamientos automáticos programados 🆕
- [ESTRATEGIA_TOP3_MODELOS.md](Docs/ESTRATEGIA_TOP3_MODELOS.md) — Sistema de protección de modelos
- [GESTION_LOGS_ENTRENAMIENTO.md](Docs/GESTION_LOGS_ENTRENAMIENTO.md) — Gestión automática de logs
- [LIMPIEZA_COMPLETADA.md](Docs/LIMPIEZA_COMPLETADA.md) — Historial de limpieza del proyecto

## 🔧 Herramientas de Desarrollo

```bash
# Verificar modelos entrenados
python scripts/verificar_ia_models.py

# Analizar entrenamientos
python scripts/visualizar_entrenamiento.py --latest

# Ver alertas del sistema 🆕
python scripts/ver_alertas.py
python scripts/ver_alertas.py --level CRITICAL
python scripts/ver_alertas.py --report

# Limpiar caché manualmente
python -m src.utils.drop_cache

# Configurar entorno inicial
python scripts/setup_entorno.py
```

## 🏗️ Arquitectura

El sistema utiliza una arquitectura modular con separación de responsabilidades:

- **src/core/** — Configuración, logging, validación y excepciones
- **src/models/** — Esquemas de datos con Pydantic
- **src/api/** — Cliente HTTP para APIs externas
- **src/excel/** — Manejo de archivos Excel
- **src/utils/** — Utilidades de entrenamiento, predicción y visualización

### Tecnologías Principales

- **Machine Learning:** scikit-learn (RandomForestClassifier, StratifiedKFold, GridSearchCV)
- **ML Avanzado:** XGBoost, LightGBM
- **Validación:** Pydantic
- **Configuración:** python-dotenv
- **Datos:** pandas, openpyxl, numpy
- **Logging:** logging (Python estándar)

## 🚨 Solución de Problemas

### Error: "Archivo Excel no encontrado"
```bash
python main.py --collect
```

### Error: "Modelos no encontrados"
```bash
python main.py --train
```

### Error: "ImportError"
```bash
pip install -r requirements.txt
```

### Limpiar y reiniciar
```bash
python -m src.utils.drop_cache
python main.py
```

## 📊 Rendimiento

- **Entrenamiento:** 8000 iteraciones por lotería (~30-60 min)
- **Predicción:** < 1 segundo por lotería
- **Accuracy objetivo:** ≥ 0.7 (70%)
- **Modelos:** RandomForest con 200 estimadores

## 🔄 Flujo de Trabajo Típico

1. **Configurar entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con tus valores
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Recolectar datos:**
   ```bash
   python main.py --collect
   ```

4. **Entrenar modelos:**
   ```bash
   python main.py --train
   ```

5. **Generar predicciones:**
   ```bash
   python main.py --predict
   ```

6. **O ejecutar todo:**
   ```bash
   python index.py
   ```

## 🧠 Autor / Créditos

Proyecto desarrollado por **Juan Sebastian Martinez Lesmes**  
Implementando técnicas de Machine Learning y procesamiento automatizado de datos para la predicción de resultados en el sector de juegos de azar.

## 📝 Licencia

Ver archivo [LICENSE](LICENSE) para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

**Versión:** 2.0 (Post-limpieza)  
**Última actualización:** Febrero 2026  
**Estado:** ✅ Producción