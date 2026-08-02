# Sistema de Predicción de Lotería

Sistema en Python para predicción de resultados de **Astro Sol** y **Astro Luna**
mediante Machine Learning con algoritmo genético, scraping incremental y
sincronización automática contra Neon PostgreSQL.

---

## Características

- RandomForest con modelo compuesto por dígitos (4 dígitos × 10 clases c/u)
- Algoritmo genético real: población → selección → cruce → mutación
- Paralelismo por generación usando todos los núcleos disponibles
- 41 features basadas en historial (sin features de calendario)
- Dos modos de entrenamiento: `test` (rápido) y `prod` (completo)
- Sincronización incremental automática con Neon PostgreSQL cada 3 días vía GitHub Actions
- Predicción con top-3 números y top-3 signos con porcentaje de confianza

---

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus valores
```

---

## Uso

### Pipeline completo

```bash
python main.py
```

Ejecuta en orden: actualizar datos → entrenar → predecir → limpiar caché.

### Comandos individuales

```bash
# Sincronizar datos con Neon PostgreSQL
python main.py --actualizar

# Entrenar modelos (modo prod por defecto)
python main.py --entrenar

# Entrenar en modo test (2 iteraciones, rápido)
python main.py --entrenar --modo test

# Entrenar en modo prod (algoritmo genético, paralelo)
python main.py --entrenar --modo prod

# Generar predicción
python main.py --predecir

# Limpiar __pycache__
python main.py --limpiar

# Ver configuración activa
python main.py --config
```

### Filtrar por lotería

```bash
python main.py --actualizar --lottery luna
python main.py --entrenar --lottery "ASTRO LUNA"
python main.py --predecir --lottery sol
```

---

## Configuración

Variables de entorno en `.env`:

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión Neon PostgreSQL | — |
| `TRAINING_MODE` | Modo de entrenamiento: `test` o `prod` | `prod` |
| `MODELS_DIR` | Carpeta de modelos | `IA_models` |
| `DATA_DIR` | Carpeta de datos | `data` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

---

## Modos de entrenamiento

| Parámetro | `test` | `prod` |
|---|---|---|
| Estrategia | Random search | Algoritmo genético |
| Iteraciones | 2 | 15 generaciones × 8 individuos |
| n_estimators | [20, 30] | [100, 150, 200, 250, 300] |
| max_depth | [3, 4] | [4, 5, 6, 8, None] |
| Paralelismo | No | Sí (todos los núcleos) |
| Early stop | No | 5 generaciones sin mejora |
| Tiempo aprox. | Segundos | ~5 minutos |

---

## Automatización — GitHub Actions

El workflow `Auto_Neon_Sync` sincroniza la base de datos automáticamente:

- Se ejecuta **cada 3 días a las 12:00 UTC**
- También ejecutable manualmente desde GitHub UI
- Requiere el secret `NEON_DATABASE_URL` en el repositorio
- Solo descarga fechas que faltan (sincronización incremental)

---

## Resultados actuales

Sobre ASTRO LUNA (996 registros):

| Métrica | Valor |
|---|---|
| Accuracy result (modo prod) | ~25% |
| Accuracy series (modo prod) | ~15% |
| Azar puro (número exacto) | 0.11% |
| Azar puro (signo) | 8.3% |

---

## Estructura del proyecto

```
Lotery_prediction/
├── main.py                      # CLI principal
├── requirements.txt
├── .env                         # Variables locales (no se sube a git)
├── .env.example                 # Plantilla de configuración
│
├── src/
│   ├── core/
│   │   ├── config.py            # Configuración centralizada + perfiles
│   │   ├── logger.py            # Logger (solo consola)
│   │   ├── exceptions.py
│   │   └── validators.py
│   ├── api/
│   │   └── superastro_scraper.py  # Scraper de superastro.com.co
│   ├── database/
│   │   ├── connection.py        # Conexión Neon PostgreSQL
│   │   ├── repository.py        # Único lugar con SQL
│   │   ├── queries.py
│   │   └── sync.py              # Orquestador de sincronización
│   ├── features/
│   │   └── feature_engineering.py  # 41 features históricas
│   ├── models/
│   │   └── schemas.py
│   └── utils/
│       ├── training_simple.py   # Entrenamiento genético con paralelismo
│       ├── prediction.py        # Motor de predicción top-3
│       ├── save_training.py     # Guardado de modelos con metadata
│       ├── alerts.py            # Alertas de rendimiento
│       └── drop_cache.py
│
├── data/
│   ├── resultados_astro.xlsx    # Histórico local (fallback)
│   └── results.json             # Predicciones generadas
│
├── IA_models/                   # Modelos entrenados (.pkl)
│   └── [1|2]_astro_luna_[result|series].pkl
│
├── scripts/
│   ├── migrar_a_neon.py         # Migración inicial Excel → Neon
│   ├── scheduler.py             # Scheduler local opcional
│   └── setup_entorno.py
│
├── .github/
│   └── workflows/
│       └── sync_neon.yml        # Auto_Neon_Sync
│
└── Docs/                        # Documentación técnica
```

---

## Documentación

| Documento | Descripción |
|---|---|
| [Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md) | Estructura del sistema, flujo de datos, esquema de base de datos, CLI completo y formato de modelos guardados |
| [Docs/FEATURES.md](Docs/FEATURES.md) | Las 41 features de entrenamiento explicadas una por una, su justificación estadística y cómo agregar nuevas sin romper los modelos |
| [Docs/MEJORAS_IA.md](Docs/MEJORAS_IA.md) | Decisiones de diseño del sistema de IA, señal estadística detectada en los datos y mejoras pendientes priorizadas |
| [Docs/MEJORAS_ML.md](Docs/MEJORAS_ML.md) | Pipeline de entrenamiento técnico, modos de entrenamiento, métricas actuales vs azar puro y cómo funciona la predicción |
| [Docs/SCHEDULER.md](Docs/SCHEDULER.md) | Automatización con GitHub Actions: configuración, frecuencia, credenciales y lógica de sincronización incremental |
| [Docs/Task_backtesting.md](Docs/Task_backtesting.md) | Plan de implementación del backtesting temporal: algoritmo paso a paso, métricas, criterios de éxito y CLI propuesto |

---

## Requisitos

- Python 3.11+
- Las dependencias se instalan con `pip install -r requirements.txt`

## Autor

**Juan Sebastian Martinez Lesmes**

## Licencia

Ver [LICENSE](LICENSE).
