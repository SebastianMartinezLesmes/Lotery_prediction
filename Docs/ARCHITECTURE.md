# Arquitectura del Sistema

Sistema de predicción de lotería colombiana (Astro Sol / Astro Luna) basado en
Machine Learning con RandomForest, scraping incremental y sincronización automática
contra Neon PostgreSQL.

---

## Estructura de directorios

```
Lotery_prediction/
│
├── main.py                      # CLI principal (--actualizar, --entrenar, --predecir, --limpiar)
├── requirements.txt             # Dependencias con versiones fijadas
├── Dockerfile                   # Imagen Docker (python:3.11-slim, usuario no-root)
├── docker-compose.yml           # Servicios: lottery-system, lottery-scheduler
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
│   │   └── superastro_scraper.py  # Scraper de superastro.com.co (1 request por ejecución)
│   │
│   ├── database/
│   │   ├── connection.py        # Conexión a Neon PostgreSQL (psycopg2)
│   │   ├── repository.py        # Acceso a datos — único lugar con SQL
│   │   ├── queries.py           # Queries SQL parametrizadas
│   │   └── sync.py              # Orquestador de sincronización incremental
│   │
│   ├── features/
│   │   └── feature_engineering.py  # Generación de 41 features históricas
│   │
│   ├── models/
│   │   └── schemas.py           # Schemas Pydantic
│   │
│   ├── utils/
│   │   ├── training_simple.py   # Entrenamiento genético por dígitos con paralelismo  ← activo
│   │   ├── prediction.py        # Motor de predicción con top-3 números y signos       ← activo
│   │   ├── save_training.py     # Guardado de modelos con metadata (2 slots por tipo)  ← activo
│   │   ├── alerts.py            # Sistema de alertas (consola + email opcional)        ← activo
│   │   ├── drop_cache.py        # Limpieza de __pycache__                             ← activo
│   │   ├── mutation.py          # Operadores genéticos (entrenamiento evolutivo)       ← legacy
│   │   ├── training.py          # Entrenamiento evolutivo completo (RF/XGB/LGBM)      ← legacy
│   │   ├── batch_prediction.py  # Predicción por lotes (usa features de calendario)   ← legacy/roto
│   │   └── training_visualizer.py  # Barra de progreso y logger JSON de métricas      ← legacy
│   │
│   └── excel/
│       ├── excel_updater.py     # Actualización incremental del Excel local
│       └── read_excel.py        # Lectura del Excel
│
├── data/
│   ├── resultados_astro.xlsx    # Histórico local (fallback cuando Neon no está disponible)
│   └── results.json             # Predicciones generadas con timestamp
│
├── IA_models/
│   ├── 1_astro_luna_result.pkl  # Slot 1 — _ModeloCompuesto (4 RF internos)
│   ├── 2_astro_luna_result.pkl  # Slot 2 — _ModeloCompuesto
│   ├── 1_astro_luna_series.pkl  # Slot 1 — RandomForestClassifier (12 signos)
│   └── 2_astro_luna_series.pkl  # Slot 2 — RandomForestClassifier
│   # Solo existen modelos para ASTRO LUNA. ASTRO SOL no tiene modelos entrenados.
│
├── scripts/
│   ├── sync_check.py            # CI: sincroniza + verifica frescura, exit 1 si falla
│   ├── migrar_a_neon.py         # Migración inicial Excel → Neon (uso único)
│   ├── scheduler.py             # Scheduler local opcional (schedule / APScheduler)
│   └── setup_entorno.py         # Setup del entorno de desarrollo
│
├── .github/
│   ├── keepalive/
│   │   └── last_alive.txt       # Timestamp ISO-8601 del último keep-alive
│   └── workflows/
│       ├── sync_neon.yml        # Auto_Neon_Sync — sincronización cada 3 días
│       └── step_alive_proyect.yml  # Step_Alive_proyect — keep-alive días 1 y 26
│
└── Docs/
    ├── ARCHITECTURE.md          # Este documento
    ├── FEATURES.md              # 41 features y su justificación estadística
    ├── MEJORAS_IA.md            # Estado del sistema de IA y decisiones de diseño
    ├── MEJORAS_ML.md            # Pipeline de ML, modos de entrenamiento, métricas
    ├── SCHEDULER.md             # Automatización con GitHub Actions (ambos workflows)
    ├── Task_backtesting.md      # Especificación de backtesting (PENDIENTE de implementar)
    ├── Task_To_Do.md            # Tareas pendientes priorizadas
    └── DOCKER.md                # Instrucciones de uso con Docker Compose
```

---

## Flujo de datos

```
superastro.com.co
      │
      ▼
SuperAstroScraper.obtener_todos_resultados_pagina()
      │   1 request HTTP por lotería — parsea tabla HTML con BeautifulSoup
      ▼
SuperAstroScraper.sincronizar_con_neon()
      │   compara con MAX(fecha) en Neon y filtra solo los nuevos
      ▼
synchronize_database()   ← src/database/sync.py
      │   orquesta el flujo para cada lotería en LOTERIAS_DISPONIBLES
      │   lanza RuntimeError si alguna lotería falla (propaga el fallo)
      ▼
LotteriaRepository.upsert_results()
      │   INSERT ON CONFLICT DO UPDATE — nunca duplica, nunca borra
      ▼
Neon PostgreSQL   ← fuente principal de datos
      │
      ▼ (fallback: data/resultados_astro.xlsx si Neon no disponible)
      │
      ▼
feature_engineering.py → generar_features(df)
      │   41 features históricas (sin calendario)
      │   reset_index(drop=True) → índice alineado con df
      ▼
training_simple.py → entrenar_modelos_por_loteria()
      │   algoritmo genético: 15 generaciones × 8 individuos
      │   split TEMPORAL: X[:split_idx] train / X[split_idx:] test
      │   5 RF en paralelo por generación (4 dígitos + series)
      │   early stop si no mejora en 5 generaciones
      ▼
save_training.py → guardar_modelo_si_mejora()
      │   2 slots por tipo, guarda solo si supera accuracy del peor slot
      ▼
IA_models/*.pkl
      │   payload: {model, accuracy, feature_names, sign_mapping, n_features, …}
      ▼
prediction.py → predecir_para_loteria()
      │   carga slot de mayor accuracy, genera features sobre historial completo
      │   toma última fila → top-3 números + top-3 signos con confianza
      ▼
data/results.json   ← predicción guardada con timestamp
```

---

## Configuración centralizada

Toda la configuración vive en `src/core/config.py` como atributos de `Settings`.
Se instancia una vez como `settings` y se importa desde cualquier módulo.

```python
from src.core.config import settings

settings.API_URL              # URL del scraper: superastro.com.co/historico.php
settings.DATABASE_URL         # Cadena de conexión Neon (desde .env)
settings.MODELS_DIR           # Ruta a IA_models/
settings.TRAINING_MODE        # 'test' o 'prod'
settings.LOTTERIES            # ['ASTRO SOL', 'ASTRO LUNA']
settings.SIGNOS               # ['ARI','TAU','GEM','CAN','LEO','VIR','LIB','ESC','SAG','CAP','ACU','PIS']
settings.get_training_profile()  # Devuelve el perfil activo (dict con hiperparámetros)
```

Variables de entorno relevantes (`.env`):

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión Neon PostgreSQL | — |
| `TRAINING_MODE` | Modo de entrenamiento: `test` o `prod` | `prod` |
| `MODELS_DIR` | Carpeta de modelos | `IA_models` |
| `DATA_DIR` | Carpeta de datos | `data` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `ALERT_ACCURACY_WARNING` | Umbral WARNING del sistema de alertas | `0.6` |
| `ALERT_ACCURACY_CRITICAL` | Umbral CRITICAL del sistema de alertas | `0.5` |
| `ALERT_EMAIL_ENABLED` | Activar notificaciones por email | `false` |

---

## CLI — Comandos disponibles

```bash
# Pipeline completo (actualizar → entrenar → predecir → limpiar)
python main.py

# Pasos individuales
python main.py --actualizar              # Sincronizar Neon
python main.py --entrenar               # Entrenar (modo prod por defecto)
python main.py --predecir               # Generar predicciones
python main.py --limpiar                # Limpiar __pycache__

# Con filtros
python main.py --actualizar --lottery luna
python main.py --entrenar --lottery "ASTRO LUNA"
python main.py --predecir --lottery "ASTRO LUNA"

# Modo de entrenamiento (sobreescribe .env)
python main.py --entrenar --modo test   # 2 iteraciones, secuencial
python main.py --entrenar --modo prod   # 15 generaciones, paralelo

# Ver configuración activa
python main.py --config
```

---

## Base de datos Neon

Esquema PostgreSQL:

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

## GitHub Actions

### Workflow 1: Auto_Neon_Sync

Archivo: `.github/workflows/sync_neon.yml`

| Propiedad | Valor |
|---|---|
| Trigger automático | `0 12 * * *` — todos los días a las 12:00 UTC |
| Trigger manual | `workflow_dispatch` con input opcional `filtro_loteria` |
| Secret requerido | `NEON_DATABASE_URL` |
| Script principal | `scripts/sync_check.py` |
| Fallo propagado | `set -euo pipefail` — cualquier error Python marca el job en rojo |
| Filtro de lotería | Variable de entorno `FILTRO` (no interpolación de strings Python) |
| Resumen | `$GITHUB_STEP_SUMMARY` con registros sincronizados y MAX(fecha) por lotería |

Qué hace `scripts/sync_check.py`:
1. Llama a `synchronize_database(filtro_loteria=filtro)` de `src/database/sync.py`
2. Imprime `TOTAL_REGISTROS=<n>` (capturado por el YAML para el resumen)
3. Verifica que `MAX(fecha)` de cada lotería sea ≥ `hoy - 3 días`
4. Sale con `exit 1` si hay excepción o si alguna fecha está vencida

### Workflow 2: Step_Alive_proyect

Archivo: `.github/workflows/step_alive_proyect.yml`

| Propiedad | Valor |
|---|---|
| Trigger automático | `0 3 1,26 * *` — días 1 y 26 de cada mes a las 03:00 UTC |
| Trigger manual | `workflow_dispatch` disponible |
| Propósito | Evitar que GitHub desactive los workflows por 60 días sin commits |
| Permiso | `contents: write` (solo `GITHUB_TOKEN`, sin secretos extra) |
| Archivo modificado | `.github/keepalive/last_alive.txt` (timestamp ISO-8601) |
| Commit | `chore: keep-alive <timestamp> [skip ci]` |

**Por qué existe**: `Auto_Neon_Sync` no hace commits. GitHub desactiva workflows con
`schedule` si el repositorio no recibe commits reales en 60 días. `Step_Alive_proyect`
genera un commit mínimo cada ≤25 días para mantener activos todos los workflows.

---

## Modelos guardados

Cada modelo se serializa con `joblib` como un `dict` con metadata completa:

```python
{
    "model":         <_ModeloCompuesto | RandomForestClassifier>,
    "accuracy":      0.2487,
    "f1_score":      None,
    "algoritmo":     "_ModeloCompuesto",
    "n_features":    41,
    "feature_names": [...],          # FEATURE_COLUMNS exactas
    "sign_mapping":  {0: "ARI", 1: "TAU", ..., 11: "PIS"},  # mapeo estable
    "n_records":     996,
    "loteria":       "ASTRO LUNA",
    "tipo_modelo":   "result",
    "params":        {...},
    "timestamp":     "2026-08-01T17:00:00"
}
```

El `sign_mapping` garantiza que el modelo de series siempre decodifique los signos
con el mismo orden con el que fue entrenado, independientemente del orden en que
lleguen los datos.

---

## Logging

El sistema usa **solo salida a consola** — no se generan archivos `.log` en el
pipeline principal. Esto es compatible con GitHub Actions y Docker, que capturan
stdout de forma nativa.

```python
from src.core.logger import LoggerManager

logger = LoggerManager.get_logger("mi_modulo")
logger.info("Mensaje informativo")
logger.error("Error ocurrido")
```

Excepción: `scripts/scheduler.py` crea `scheduler.log` cuando se ejecuta localmente.

---

## Docker

Ver `Docs/DOCKER.md` para instrucciones completas.

Servicios en `docker-compose.yml`:
- `lottery-system` — ejecuta `python main.py` (pipeline completo una vez)
- `lottery-scheduler` — ejecuta `python scripts/scheduler.py` (daemon periódico)

> **Nota**: el `docker-compose.yml` actual tiene `API_URL` apuntando a una URL de API
> externa que ya no se usa. El scraper usa `BASE_URL` (por defecto `superastro.com.co`).
> Ver tarea pendiente T-DOCKER en `Task_To_Do.md`.
