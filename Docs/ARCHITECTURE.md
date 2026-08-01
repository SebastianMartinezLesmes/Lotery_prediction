# Arquitectura del Sistema

Sistema de predicción de lotería colombiana (Astro Sol / Astro Luna) basado en
Machine Learning con RandomForest, scraping incremental y sincronización automática
contra Neon PostgreSQL.

---

## Estructura de directorios

```
Lotery_prediction/
│
├── main.py                      # CLI principal (--actualizar, --entrenar, --predecir)
├── requirements.txt
├── .env                         # Variables de entorno locales (no se sube a git)
├── .env.example                 # Plantilla de configuración
│
├── src/
│   ├── core/
│   │   ├── config.py            # Configuración centralizada + perfiles de entrenamiento
│   │   ├── logger.py            # Logger solo-consola (sin archivos .log)
│   │   ├── exceptions.py        # Jerarquía de excepciones personalizadas
│   │   └── validators.py        # Validadores de datos
│   │
│   ├── api/
│   │   └── superastro_scraper.py  # Scraper de superastro.com.co
│   │
│   ├── database/
│   │   ├── connection.py        # Conexión a Neon PostgreSQL (psycopg2)
│   │   ├── repository.py        # Acceso a datos — único lugar con SQL
│   │   ├── queries.py           # Queries SQL parametrizadas
│   │   └── sync.py              # Orquestador de sincronización
│   │
│   ├── features/
│   │   └── feature_engineering.py  # Generación de features históricas (41 features)
│   │
│   ├── models/
│   │   └── schemas.py           # Schemas Pydantic
│   │
│   ├── utils/
│   │   ├── training_simple.py   # Entrenamiento por dígitos con paralelismo
│   │   ├── prediction.py        # Motor de predicción con top-3
│   │   ├── save_training.py     # Guardado de modelos con metadata
│   │   ├── alerts.py            # Sistema de alertas (consola + email opcional)
│   │   ├── mutation.py          # Entrenamiento evolutivo (genético)
│   │   ├── batch_prediction.py  # Predicción por lotes
│   │   ├── training.py          # Entrenamiento completo (RF evolutivo)
│   │   ├── training_visualizer.py  # Visualización del progreso
│   │   └── drop_cache.py        # Limpieza de __pycache__
│   │
│   └── excel/
│       ├── excel_updater.py     # Actualización del Excel local
│       └── read_excel.py        # Lectura del Excel
│
├── data/
│   ├── resultados_astro.xlsx    # Histórico local (fallback cuando Neon no está disponible)
│   └── results.json             # Predicciones generadas
│
├── IA_models/
│   ├── 1_astro_luna_result.pkl  # Slot 1 — modelo result ASTRO LUNA
│   ├── 2_astro_luna_result.pkl  # Slot 2 — modelo result ASTRO LUNA
│   ├── 1_astro_luna_series.pkl  # Slot 1 — modelo series ASTRO LUNA
│   └── 2_astro_luna_series.pkl  # Slot 2 — modelo series ASTRO LUNA
│
├── scripts/
│   ├── migrar_a_neon.py         # Migración inicial Excel → Neon
│   ├── scheduler.py             # Scheduler local (opcional)
│   └── setup_entorno.py         # Setup del entorno
│
├── .github/
│   └── workflows/
│       └── sync_neon.yml        # GitHub Actions: Auto_Neon_Sync (cada 3 días)
│
└── Docs/
    ├── ARCHITECTURE.md          # Este documento
    ├── MEJORAS_IA.md            # Estado del sistema de IA y mejoras
    ├── MEJORAS_ML.md            # Estado del ML y decisiones técnicas
    ├── FEATURES.md              # Features de entrenamiento y su justificación
    └── SCHEDULER.md             # Automatización con GitHub Actions
```

---

## Flujo de datos

```
superastro.com.co
      │
      ▼
SuperAstroScraper          ← 1 request por ejecución, parsea tabla HTML
      │
      ▼
sincronizar_con_neon()     ← obtiene MAX(fecha) de Neon, filtra solo lo nuevo
      │
      ▼
LotteriaRepository         ← upsert_results() — INSERT ON CONFLICT DO UPDATE
      │
      ▼
Neon PostgreSQL            ← fuente principal de datos
      │
      ▼ (fallback: Excel local si Neon no está disponible)
      │
      ▼
feature_engineering.py     ← genera 41 features históricas
      │
      ▼
training_simple.py         ← entrena 5 RF (4 dígitos + series) en paralelo
      │
      ▼
IA_models/*.pkl            ← 2 slots por tipo de modelo, guarda si mejora
      │
      ▼
prediction.py              ← carga mejor modelo, predice top-3 números + signos
      │
      ▼
data/results.json          ← resultado guardado con timestamp y confianza
```

---

## Configuración centralizada

Toda la configuración vive en `src/core/config.py` como atributos de la clase `Settings`.
Se instancia una vez como `settings` y se importa desde cualquier módulo.

```python
from src.core.config import settings

settings.API_URL          # URL del scraper
settings.DATABASE_URL     # Cadena de conexión Neon (desde .env)
settings.MODELS_DIR       # Ruta a IA_models/
settings.TRAINING_MODE    # 'test' o 'prod'
settings.get_training_profile()  # Devuelve el perfil activo
```

Variables de entorno relevantes (definidas en `.env`):

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión Neon PostgreSQL | — |
| `TRAINING_MODE` | Modo de entrenamiento: `test` o `prod` | `prod` |
| `MODELS_DIR` | Carpeta de modelos | `IA_models` |
| `DATA_DIR` | Carpeta de datos | `data` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

---

## CLI — Comandos disponibles

```bash
# Pipeline completo (actualizar → entrenar → predecir → limpiar)
python main.py

# Pasos individuales
python main.py --actualizar              # Sincronizar con Neon
python main.py --entrenar               # Entrenar modelos (modo prod por defecto)
python main.py --predecir               # Generar predicción
python main.py --limpiar                # Limpiar __pycache__

# Con filtros
python main.py --entrenar --lottery luna
python main.py --predecir --lottery "ASTRO LUNA"

# Modo de entrenamiento (sobreescribe .env)
python main.py --entrenar --modo test   # Rápido, 2 iteraciones
python main.py --entrenar --modo prod   # Completo, paralelo con early stop

# Ver configuración activa
python main.py --config
```

---

## Base de datos Neon

Esquema en PostgreSQL:

```sql
loterias   (id, nombre)
signos     (id, codigo CHAR(3), nombre)
resultados (id, fecha DATE, loteria_id, result SMALLINT, signo_id)
           UNIQUE (fecha, loteria_id)

-- Vista de conveniencia
v_resultados  →  fecha, lottery, result, series
```

La constraint `UNIQUE (fecha, loteria_id)` garantiza que nunca haya duplicados
aunque el workflow se ejecute varias veces en el mismo día.

---

## GitHub Actions — Auto_Neon_Sync

Workflow en `.github/workflows/sync_neon.yml`:

- Se ejecuta **cada 3 días a las 12:00 UTC** (`0 12 */3 * *`)
- También ejecutable manualmente desde GitHub UI (`workflow_dispatch`)
- Requiere el secret `NEON_DATABASE_URL` configurado en el repositorio
- Hace **sincronización incremental**: solo descarga fechas que faltan en Neon
- Incluye cache de pip para ejecuciones más rápidas
- Genera un resumen en la pestaña de Actions con registros sincronizados

---

## Logging

El sistema usa **solo salida a consola** — no se generan archivos `.log`.
Esto simplifica el proyecto y es compatible con GitHub Actions y Docker,
que capturan stdout de forma nativa.

```python
from src.core.logger import LoggerManager

logger = LoggerManager.get_logger("mi_modulo")
logger.info("Mensaje informativo")
logger.error("Error ocurrido")
```

---

## Modelos guardados

Cada modelo se guarda como un payload `dict` serializado con `joblib`:

```python
{
    "model":         <objeto sklearn>,
    "accuracy":      0.2487,
    "f1_score":      None,
    "algoritmo":     "_ModeloCompuesto",
    "n_features":    41,
    "feature_names": [...],   # FEATURE_COLUMNS exactas con las que se entrenó
    "n_records":     996,
    "loteria":       "ASTRO LUNA",
    "tipo_modelo":   "result",
    "params":        {...},
    "timestamp":     "2026-08-01T17:00:00"
}
```

Hay 2 slots por modelo. Al entrenar, se reemplaza el slot con menor accuracy
solo si el nuevo modelo lo supera. Esto garantiza que `IA_models/` siempre
tenga los 2 mejores modelos encontrados históricamente.
