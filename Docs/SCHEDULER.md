# ⏰ Scheduler - Entrenamientos Automáticos

## Descripción

Sistema de programación automática para ejecutar entrenamientos, recolección de datos y pipeline completo de forma periódica sin intervención manual.

---

## ✨ Características

- **Múltiples backends**: schedule, APScheduler, cron
- **Tareas configurables**: Entrenamiento, recolección, pipeline completo
- **Expresiones cron**: Programación flexible
- **Shutdown graceful**: Manejo de señales SIGINT/SIGTERM
- **Logging completo**: Registro de todas las ejecuciones
- **Timeout protection**: Límites de tiempo por tarea
- **Docker ready**: Integración con Docker Compose

---

## 🚀 Inicio Rápido

### Opción 1: Scheduler Simple (schedule)

```bash
# Instalar dependencia
pip install schedule

# Ejecutar
python scripts/scheduler.py --mode simple
```

### Opción 2: Scheduler Avanzado (APScheduler)

```bash
# Instalar dependencia
pip install apscheduler

# Ejecutar
python scripts/scheduler.py --mode apscheduler
```

### Opción 3: Cron (Linux/Mac)

```bash
# Generar crontab
python scripts/scheduler.py --mode crontab

# Instalar crontab
crontab crontab.txt

# Verificar
crontab -l
```

---

## ⚙️ Configuración

### Variables de Entorno

Agregar al archivo `.env`:

```env
# Schedule Simple
SCHEDULE_COLLECT_DAILY=08:00
SCHEDULE_TRAIN_WEEKLY="Sunday 02:00"

# APScheduler (formato cron: minuto hora dia mes dia_semana)
SCHEDULE_COLLECT_CRON="0 8 * * *"      # Diario 8:00 AM
SCHEDULE_TRAIN_CRON="0 2 * * 0"        # Domingos 2:00 AM
SCHEDULE_PIPELINE_CRON="0 3 1 * *"     # Día 1 de cada mes 3:00 AM
```

### Formato Cron

```
┌───────────── minuto (0 - 59)
│ ┌───────────── hora (0 - 23)
│ │ ┌───────────── día del mes (1 - 31)
│ │ │ ┌───────────── mes (1 - 12)
│ │ │ │ ┌───────────── día de la semana (0 - 6) (Domingo=0)
│ │ │ │ │
* * * * *
```

**Ejemplos:**
- `0 8 * * *` - Todos los días a las 8:00 AM
- `0 2 * * 0` - Todos los domingos a las 2:00 AM
- `0 3 1 * *` - Día 1 de cada mes a las 3:00 AM
- `*/30 * * * *` - Cada 30 minutos
- `0 */6 * * *` - Cada 6 horas
- `0 0 * * 1-5` - Lunes a viernes a medianoche

---

## 📋 Tareas Disponibles

### 1. Recolección de Datos

Ejecuta `python main.py --collect`

**Configuración:**
```env
SCHEDULE_COLLECT_CRON="0 8 * * *"  # Diario 8:00 AM
```

**Uso:**
- Actualiza datos desde la API
- Genera archivo Excel actualizado
- Timeout: 10 minutos

### 2. Entrenamiento de Modelos

Ejecuta `python main.py --train`

**Configuración:**
```env
SCHEDULE_TRAIN_CRON="0 2 * * 0"  # Domingos 2:00 AM
```

**Uso:**
- Entrena todos los modelos
- Genera alertas si rendimiento bajo
- Timeout: 2 horas

### 3. Pipeline Completo

Ejecuta `python index.py`

**Configuración:**
```env
SCHEDULE_PIPELINE_CRON="0 3 1 * *"  # Mensual
```

**Uso:**
- Dependencias + Recolección + Predicción
- Limpieza de caché
- Timeout: 1 hora

---

## 🔧 Uso Detallado

### Scheduler Simple (schedule)

**Ventajas:**
- Fácil de usar
- Sintaxis legible
- Ideal para desarrollo

**Limitaciones:**
- No soporta días del mes específicos
- Menos opciones de configuración

**Ejemplo:**
```python
import schedule

# Cada día a las 8:00
schedule.every().day.at("08:00").do(ejecutar_recoleccion)

# Cada domingo a las 2:00
schedule.every().sunday.at("02:00").do(ejecutar_entrenamiento)

# Cada hora
schedule.every().hour.do(ejecutar_prediccion)

# Cada 30 minutos
schedule.every(30).minutes.do(verificar_alertas)
```

### Scheduler Avanzado (APScheduler)

**Ventajas:**
- Expresiones cron completas
- Múltiples triggers
- Persistencia de jobs
- Ideal para producción

**Ejemplo:**
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BlockingScheduler()

# Diario 8:00 AM
scheduler.add_job(
    ejecutar_recoleccion,
    CronTrigger.from_crontab("0 8 * * *"),
    id='recoleccion_diaria'
)

# Domingos 2:00 AM
scheduler.add_job(
    ejecutar_entrenamiento,
    CronTrigger.from_crontab("0 2 * * 0"),
    id='entrenamiento_semanal'
)

scheduler.start()
```

### Cron (Linux/Mac)

**Ventajas:**
- Nativo del sistema operativo
- Muy confiable
- No requiere proceso Python corriendo

**Archivo crontab generado:**
```cron
# Recolección diaria 8:00 AM
0 8 * * * cd /path/to/project && python main.py --collect >> logs/cron.log 2>&1

# Entrenamiento semanal (domingos 2:00 AM)
0 2 * * 0 cd /path/to/project && python main.py --train >> logs/cron.log 2>&1

# Pipeline mensual (día 1, 3:00 AM)
0 3 1 * * cd /path/to/project && python index.py >> logs/cron.log 2>&1
```

**Comandos útiles:**
```bash
# Ver crontab actual
crontab -l

# Editar crontab
crontab -e

# Eliminar crontab
crontab -r

# Ver logs de cron
tail -f /var/log/syslog | grep CRON
```

---

## 🐳 Docker Integration

### Docker Compose

El servicio `lottery-scheduler` ejecuta el scheduler automáticamente:

```yaml
lottery-scheduler:
  image: lottery-prediction:latest
  command: python scripts/scheduler.py --mode apscheduler
  restart: unless-stopped
```

**Comandos:**
```bash
# Iniciar scheduler
docker-compose up -d lottery-scheduler

# Ver logs
docker-compose logs -f lottery-scheduler

# Detener
docker-compose stop lottery-scheduler

# Reiniciar
docker-compose restart lottery-scheduler
```

---

## 🧪 Testing

### Ejecutar Tarea Inmediatamente

```bash
# Probar pipeline
python scripts/scheduler.py --run pipeline

# Probar entrenamiento
python scripts/scheduler.py --run train

# Probar recolección
python scripts/scheduler.py --run collect
```

### Verificar Configuración

```bash
# Ver próximas ejecuciones (APScheduler)
python scripts/scheduler.py --mode apscheduler
# Presionar Ctrl+C después de ver el listado
```

---

## 📊 Monitoreo

### Logs

Todos los eventos se registran en `logs/scheduler.log`:

```bash
# Ver logs en tiempo real
tail -f logs/scheduler.log

# Buscar errores
grep ERROR logs/scheduler.log

# Ver últimas 50 líneas
tail -n 50 logs/scheduler.log
```

### Formato de Logs

```
2026-02-27 08:00:00 - scheduler - INFO - Iniciando recolección de datos programada
2026-02-27 08:00:15 - scheduler - INFO - Recolección completada exitosamente
2026-02-27 02:00:00 - scheduler - INFO - Iniciando entrenamiento programado
2026-02-27 03:45:30 - scheduler - INFO - Entrenamiento completado exitosamente
```

### Alertas de Scheduler

El scheduler puede generar alertas si:
- Una tarea falla
- Una tarea excede el timeout
- Hay errores de ejecución

---

## 🔄 Casos de Uso

### 1. Actualización Diaria de Datos

```env
SCHEDULE_COLLECT_CRON="0 8 * * *"
```

Recolecta datos nuevos cada mañana a las 8:00 AM.

### 2. Entrenamiento Semanal

```env
SCHEDULE_TRAIN_CRON="0 2 * * 0"
```

Re-entrena modelos cada domingo a las 2:00 AM cuando hay menos carga.

### 3. Mantenimiento Mensual

```env
SCHEDULE_PIPELINE_CRON="0 3 1 * *"
```

Ejecuta pipeline completo el primer día de cada mes.

### 4. Predicciones Frecuentes

```env
SCHEDULE_PREDICT_CRON="0 */6 * * *"
```

Genera predicciones cada 6 horas.

### 5. Backup Automático

```cron
# Backup diario a las 4:00 AM
0 4 * * * cd /path/to/project && tar czf backups/backup-$(date +\%Y\%m\%d).tar.gz IA_models data
```

---

## 🚨 Troubleshooting

### Problema: Scheduler no inicia

```bash
# Verificar dependencias
pip install schedule apscheduler

# Ver logs
python scripts/scheduler.py --mode simple
```

### Problema: Tareas no se ejecutan

```bash
# Verificar configuración
echo $SCHEDULE_COLLECT_CRON

# Probar manualmente
python scripts/scheduler.py --run collect
```

### Problema: Timeout en entrenamiento

Ajustar timeout en `scripts/scheduler.py`:

```python
result = subprocess.run(
    [sys.executable, "main.py", "--train"],
    timeout=7200  # Aumentar a 3 horas
)
```

### Problema: Cron no ejecuta

```bash
# Verificar servicio cron
sudo service cron status

# Ver logs de cron
grep CRON /var/log/syslog

# Verificar permisos
ls -la /path/to/project
```

---

## 🔒 Seguridad

### Permisos

```bash
# Dar permisos de ejecución
chmod +x scripts/scheduler.py

# Ejecutar como usuario específico
sudo -u lottery python scripts/scheduler.py
```

### Secrets

No incluir credenciales en crontab. Usar variables de entorno:

```cron
# Cargar .env antes de ejecutar
0 8 * * * cd /path/to/project && source .env && python main.py --collect
```

---

## 📈 Mejores Prácticas

1. **Horarios off-peak**: Programar entrenamientos en horarios de baja carga
2. **Timeouts**: Configurar límites de tiempo para evitar bloqueos
3. **Logging**: Registrar todas las ejecuciones
4. **Monitoreo**: Revisar logs regularmente
5. **Alertas**: Configurar notificaciones para fallos
6. **Backup**: Respaldar modelos antes de re-entrenar
7. **Testing**: Probar tareas manualmente antes de programar
8. **Redundancia**: Usar múltiples métodos de programación

---

## 🔄 Migración

### De Cron a APScheduler

```bash
# 1. Generar crontab actual
crontab -l > old_crontab.txt

# 2. Convertir a formato APScheduler
# Editar .env con expresiones cron

# 3. Iniciar APScheduler
python scripts/scheduler.py --mode apscheduler

# 4. Verificar funcionamiento

# 5. Eliminar crontab antiguo
crontab -r
```

---

## 📚 Referencias

- [schedule Documentation](https://schedule.readthedocs.io/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Cron Expression](https://crontab.guru/)

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Estado:** ✅ Producción
