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
