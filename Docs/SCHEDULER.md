# Automatización — GitHub Actions

El sistema de actualización automática corre en GitHub Actions.
No hay scheduler local — toda la automatización es declarativa en el workflow.

---

## Workflow: Auto_Neon_Sync

Archivo: `.github/workflows/sync_neon.yml`

### Cuándo se ejecuta

| Trigger | Configuración |
|---|---|
| Automático | Cada 3 días a las **12:00 UTC** (`0 12 */3 * *`) |
| Manual | Desde GitHub → Actions → Auto_Neon_Sync → Run workflow |

### Qué hace

1. Checkout del repositorio
2. Instala Python 3.11 + dependencias (con cache de pip)
3. Llama a `synchronize_database()` de `src/database/sync.py`
4. La función obtiene `MAX(fecha)` de Neon para cada lotería
5. Descarga solo los registros que faltan desde SuperAstro
6. Hace upsert en Neon (nunca duplica, nunca borra)
7. Genera un resumen visible en la pestaña de Actions

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

### Resumen de ejecución

Cada run genera un resumen en la pestaña Summary de GitHub Actions:

```
🎯 Sincronización Neon — 2026-08-01 12:00 UTC

| Campo                   | Valor              |
|-------------------------|--------------------|
| Registros sincronizados | 6                  |
| Filtro aplicado         | Todas las loterías |
| Trigger                 | schedule           |
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
3. Hace 1 solo request a superastro.com.co
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

---

## Frecuencia y cron

La expresión `0 12 */3 * *` ejecuta los días 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31
de cada mes a las 12:00 UTC. Es la aproximación más cercana a "cada 3 días exactos"
que soporta la sintaxis cron estándar.

Para cambiar la frecuencia, editar la línea `cron:` en el workflow:

```yaml
# Ejemplos
- cron: '0 12 */3 * *'   # cada 3 días al mediodía UTC (actual)
- cron: '0 12 */2 * *'   # cada 2 días
- cron: '0 12 * * *'     # diario
- cron: '0 12 * * 1'     # cada lunes
```

---

## Credenciales — buenas prácticas

- La URL de Neon **nunca debe estar en código ni en el repositorio**
- Se gestiona exclusivamente como secret en GitHub Actions
- Localmente se define en `.env` (que está en `.gitignore`)
- El archivo `z_cred` también está en `.gitignore` — sirve como referencia
  local sin credenciales reales

Si se sospecha que la URL fue expuesta (ej. commiteada por error):
1. Ir a Neon Dashboard → proyecto → Settings → Reset password
2. Actualizar el secret `NEON_DATABASE_URL` en GitHub con la nueva URL
3. Actualizar el `.env` local

---

## Scheduler local (opcional)

`scripts/scheduler.py` existe como alternativa local si se necesita ejecutar
el pipeline en un servidor propio sin GitHub Actions. No está integrado en el
workflow principal.

Para ejecutarlo localmente:
```bash
python scripts/scheduler.py
```

Para producción en servidor propio se recomienda usar GitHub Actions
en vez del scheduler local — es más simple, no requiere un proceso
corriendo 24/7 y tiene logs integrados.

---

## Keep-alive del repositorio

### Problema

GitHub desactiva automáticamente los workflows con `schedule` cuando el repositorio pasa **60 días sin actividad**. El workflow `Auto_Neon_Sync` se ejecuta cada 3 días pero **no hace commits**, por lo que su ejecución no cuenta como actividad para GitHub. Pasados 60 días sin un commit real, GitHub desactiva todos los workflows programados del repositorio.

### Solución: workflow `Step_Alive_proyect`

Archivo: `.github/workflows/step_alive_proyect.yml`

Este workflow hace un commit mínimo (sin valor funcional) cada ~25 días para que GitHub registre actividad real y mantenga activos todos los workflows.

### Cron

```
0 3 1,26 * *
```

Se ejecuta los **días 1 y 26** de cada mes a las 03:00 UTC:

- Intervalo máximo entre ejecuciones: **25 días** (del día 1 al 26).
- Del 26 al 1 del mes siguiente son 5–6 días.
- Siempre queda muy por debajo del límite de 60 días, incluso si falla una ejecución.

> **Nota:** `*/25` en el campo día-del-mes **no** significa "cada 25 días" — significa los días 1 y 26 pero reinicia cada mes de forma irregular. Por eso se usan días explícitos `1,26`.

### Archivo modificado

`.github/keepalive/last_alive.txt` — contiene únicamente el timestamp UTC de la última ejecución en formato ISO-8601 (ej. `2026-10-04T04:01:45Z`). Es el único archivo que modifica este workflow.

### Características

| Propiedad | Valor |
|-----------|-------|
| Trigger automático | `0 3 1,26 * *` (días 1 y 26 de cada mes) |
| Trigger manual | `workflow_dispatch` disponible |
| Permiso requerido | `contents: write` (solo `GITHUB_TOKEN`, sin secretos extra) |
| Mensaje de commit | `chore: keep-alive <timestamp> [skip ci]` |
| Autor del commit | `github-actions[bot]` |
| Archivos tocados | Solo `.github/keepalive/last_alive.txt` |

### Consideraciones

- Genera ~1–2 commits por mes en `master`. Es el costo aceptado de esta estrategia.
- El `[skip ci]` en el mensaje evita que el propio commit dispare otros workflows con costes de cómputo.
- Si `master` tiene branch protection que bloquea pushes directos del bot, se debe permitir que `github-actions[bot]` omita la regla (o usar un PAT, fuera del alcance actual).
- En GitHub → Settings → Actions → General → Workflow permissions debe estar habilitado "Read and write permissions".
