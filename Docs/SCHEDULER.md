# Automatización — GitHub Actions

El sistema de actualización automática corre en GitHub Actions.
No hay scheduler local obligatorio — toda la automatización principal es declarativa.

---

## Workflow: Auto_Neon_Sync

Archivo: `.github/workflows/sync_neon.yml`

### Cuándo se ejecuta

| Trigger | Configuración |
|---|---|
| Automático | Diario a las **12:00 UTC** (`0 12 * * *`) |
| Manual | Desde GitHub → Actions → Auto_Neon_Sync → Run workflow |

### Qué hace

1. Checkout del repositorio
2. Instala Python 3.11 + dependencias (con cache de pip)
3. Ejecuta `scripts/sync_check.py` con `set -euo pipefail`
4. `sync_check.py` llama a `synchronize_database()` de `src/database/sync.py`
5. `synchronize_database()` obtiene `MAX(fecha)` de Neon para cada lotería
6. Descarga solo los registros que faltan desde SuperAstro
7. Hace upsert en Neon (nunca duplica, nunca borra)
8. Verifica que `MAX(fecha)` sea ≥ `hoy - 3 días`; si no, falla con `exit 1`
9. Genera un resumen visible en la pestaña de Actions

### Configuración requerida

En GitHub → Settings → Secrets and variables → Actions:

```
NEON_DATABASE_URL = postgresql://usuario:password@host.neon.tech/dbname?sslmode=require
```

El workflow mapea el secret a la variable de entorno `DATABASE_URL`,
que es la que lee `NeonConnection` internamente.

### Ejecución manual con filtro

Desde GitHub UI al ejecutar manualmente, se puede pasar un filtro de lotería:

```
filtro_loteria: luna     → solo ASTRO LUNA
filtro_loteria: sol      → solo ASTRO SOL
filtro_loteria: (vacío)  → todas las loterías
```

El filtro se pasa via variable de entorno `FILTRO`, no como interpolación de
texto dentro del código Python, lo que evita cualquier riesgo de inyección.

### Resumen de ejecución

Cada run genera un resumen en la pestaña Summary de GitHub Actions:

```
🎯 Sincronización Neon — 2026-10-04 12:00 UTC

| Campo                   | Valor              |
|-------------------------|--------------------|
| Registros sincronizados | 6                  |
| Filtro aplicado         | Todas las loterías |
| Trigger                 | schedule           |

### Fechas máximas por lotería

ASTRO LUNA           | 2026-10-03   | OK
ASTRO SOL            | 2026-10-03   | OK
```

---

## Lógica de sincronización incremental

El workflow **nunca descarga todo el histórico** en cada ejecución.

Flujo en `SuperAstroScraper.sincronizar_con_neon()`:

```
1. ultima_fecha = repository.get_last_date(loteria)
        ↓
2. Si ultima_fecha >= ayer → ya actualizado, retorna 0
        ↓
3. Hace 1 solo request a superastro.com.co/historico.php
        ↓
4. Filtra resultados con fecha > ultima_fecha
        ↓
5. repository.upsert_results(nuevos)
        ↓
6. Retorna cantidad de registros insertados/actualizados
```

Esto garantiza:
- Mínimo tráfico de red (1 request por lotería)
- Sin duplicados (constraint UNIQUE en la DB)
- Sin borrados accidentales
- Idempotente: ejecutar N veces da el mismo resultado

Si todas las loterías están actualizadas, el script retorna `total = 0`.
Esto es **normal y esperado** — el job termina en verde. Solo falla si hay
una excepción o si `MAX(fecha)` está vencida (ver criterios de fallo abajo).

---

## Script sync_check.py

Archivo: `scripts/sync_check.py`

Es el punto de entrada real del workflow. Hace tres cosas:

1. **Sincroniza**: llama a `synchronize_database()` y captura excepciones
2. **Imprime**: `TOTAL_REGISTROS=<n>` (capturado por el YAML para el resumen)
3. **Verifica frescura**: compara `MAX(fecha)` de cada lotería con `hoy - 3 días`

Criterios de fallo (`exit 1`):
- Excepción durante la sincronización
- `MAX(fecha)` de cualquier lotería es anterior a `hoy - 3 días`

**Nota:** `total == 0` ya **no** es criterio de fallo. Si la base está al día
o el sitio no publicó resultados nuevos ese día, 0 registros es correcto.

Uso local:
```bash
FILTRO="luna" python scripts/sync_check.py   # solo ASTRO LUNA
python scripts/sync_check.py                  # todas las loterías
```

---

## Frecuencia y cron

La expresión `0 12 * * *` ejecuta el workflow todos los días a las 12:00 UTC.
La sincronización es incremental e idempotente: si la base ya está al día,
el script retorna 0 registros sin error y el job termina en verde.

Para cambiar la frecuencia, editar la línea `cron:` en `sync_neon.yml`:

```yaml
# Ejemplos
- cron: '0 12 * * *'     # diario al mediodía UTC (actual)
- cron: '0 12 */2 * *'   # cada 2 días
- cron: '0 12 */3 * *'   # cada 3 días
- cron: '0 12 * * 1'     # cada lunes
```

---

## Credenciales — buenas prácticas

- La URL de Neon **nunca debe estar en código ni en el repositorio**
- Se gestiona exclusivamente como secret `NEON_DATABASE_URL` en GitHub Actions
- Localmente se define en `.env` (que está en `.gitignore`)

Si se sospecha que la URL fue expuesta:
1. Ir a Neon Dashboard → proyecto → Settings → Reset password
2. Actualizar el secret `NEON_DATABASE_URL` en GitHub con la nueva URL
3. Actualizar el `.env` local

---

## Workflow: Step_Alive_proyect

Archivo: `.github/workflows/step_alive_proyect.yml`

### Problema que resuelve

GitHub desactiva automáticamente los workflows con `schedule` cuando el repositorio
pasa **60 días sin actividad**. `Auto_Neon_Sync` se ejecuta cada 3 días pero
**no hace commits**, por lo que su ejecución no cuenta como actividad para GitHub.

### Solución

`Step_Alive_proyect` hace un commit mínimo cada ~25 días para que GitHub registre
actividad real y mantenga activos todos los workflows.

### Cron

```
0 3 1,26 * *
```

Se ejecuta los **días 1 y 26** de cada mes a las 03:00 UTC:

- Intervalo máximo entre ejecuciones: **25 días** (del día 1 al 26)
- Del 26 al 1 del mes siguiente son 5–6 días
- Siempre queda muy por debajo del límite de 60 días, incluso si falla una ejecución

> **Nota:** `*/25` en el campo día-del-mes **no** significa "cada 25 días" — significa
> los días 1 y 26 pero reinicia cada mes de forma irregular. Por eso se usan días
> explícitos `1,26`.

### Archivo modificado

`.github/keepalive/last_alive.txt` — contiene únicamente el timestamp UTC de la
última ejecución en formato ISO-8601 (ej. `2026-10-04T04:01:45Z`). Es el único
archivo que modifica este workflow.

### Características

| Propiedad | Valor |
|-----------|-------|
| Trigger automático | `0 3 1,26 * *` (días 1 y 26 de cada mes) |
| Trigger manual | `workflow_dispatch` disponible |
| Permiso requerido | `contents: write` (solo `GITHUB_TOKEN`) |
| Mensaje de commit | `chore: keep-alive <timestamp> [skip ci]` |
| Autor del commit | `github-actions[bot]` |
| Archivos tocados | Solo `.github/keepalive/last_alive.txt` |

### Consideraciones

- Genera ~2 commits por mes en `master`. Es el costo aceptado de esta estrategia.
- El `[skip ci]` en el mensaje evita que el propio commit dispare otros workflows.
- Si `master` tiene branch protection que bloquea pushes directos del bot, se debe
  permitir que `github-actions[bot]` omita la regla, o usar un PAT.
- En GitHub → Settings → Actions → General → Workflow permissions debe estar
  habilitado "Read and write permissions".

---

## Scheduler local (opcional)

`scripts/scheduler.py` existe como alternativa local para ejecutar el pipeline
en un servidor propio sin GitHub Actions. Soporta tres backends:

- `schedule` — cron simple en Python (requiere `pip install schedule`)
- `APScheduler` — cron avanzado con más opciones (requiere `pip install apscheduler`)
- `crontab` — genera un archivo crontab para Linux/Mac

Para usarlo:
```bash
python scripts/scheduler.py --mode simple        # scheduler Python
python scripts/scheduler.py --mode apscheduler   # APScheduler
python scripts/scheduler.py --mode crontab       # generar crontab.txt
python scripts/scheduler.py --run pipeline       # ejecutar una vez (testing)
```

Para producción en servidor propio se recomienda usar GitHub Actions
en vez del scheduler local — es más simple, no requiere un proceso
corriendo 24/7 y tiene logs integrados.

---

## Correcciones aplicadas (2026-10-03)

### Causa raíz del desfase 2026-07-12 → 2026-10-03

Se identificaron tres causas que hacían que el workflow quedara en verde aunque fallara:

1. **Excepciones tragadas en `sync.py`**: el bucle capturaba cualquier excepción,
   guardaba `-1` en métricas, y retornaba igualmente con exit 0.

2. **Sin `set -euo pipefail`**: un fallo del proceso Python no propagaba el código
   de salida al step de Actions.

3. **Interpolación del filtro**: `'$FILTRO'` se insertaba dentro del string Python,
   lo que permitía inyección de código.

### Cambios aplicados

| Archivo | Cambio |
|---------|--------|
| `src/database/sync.py` | Lanza `RuntimeError` si alguna lotería tiene métrica `-1` |
| `src/api/superastro_scraper.py` | `obtener_todos_resultados_pagina` lanza `APIError` en vez de retornar `[]` |
| `scripts/sync_check.py` | Script nuevo: ejecuta sync, imprime tabla lotería/fecha, sale con `exit 1` si hay error |
| `.github/workflows/sync_neon.yml` | Añade `set -euo pipefail`, pasa `FILTRO` por variable de entorno, llama a `sync_check.py` |

### Umbral de frescura: N = 3 días

`scripts/sync_check.py` comprueba que `MAX(fecha)` de cada lotería sea ≥ `hoy - 3 días`.
Si no lo es, el script termina con `exit 1`, marcando el step de Actions como fallido.

### Nota sobre el hueco 2026-07-12 → 2026-10-03

El sitio `superastro.com.co/historico.php` solo publica el histórico disponible
en la página en el momento de la consulta. Si el sitio no conserva resultados de
más de ~30 días, los ~83 días perdidos pueden no ser recuperables de forma automática.

Pasos recomendados:
1. Verificar manualmente si el sitio muestra resultados anteriores al 2026-09-01.
2. Si los muestra, ejecutar el workflow manualmente (`workflow_dispatch`).
3. Si el sitio no los muestra, considerar fuentes alternativas o aceptar el hueco.
