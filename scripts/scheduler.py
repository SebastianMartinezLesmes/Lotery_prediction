"""
Scheduler para entrenamientos automáticos periódicos.
Soporta múltiples backends: schedule, APScheduler, cron.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import time
import signal

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.logger import LoggerManager
from src.core.config import settings

logger = LoggerManager.get_logger("scheduler", "scheduler.log")


class GracefulKiller:
    """Maneja señales de terminación para shutdown graceful."""
    
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        logger.info(f"Señal {signum} recibida, terminando gracefully...")
        self.kill_now = True


def ejecutar_pipeline_completo():
    """Ejecuta el pipeline completo del sistema."""
    logger.info("="*70)
    logger.info("Iniciando ejecución programada del pipeline")
    logger.info("="*70)
    
    try:
        # Importar aquí para evitar problemas de importación circular
        import subprocess
        
        # Ejecutar el pipeline usando main.py
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hora máximo
        )
        
        if result.returncode == 0:
            logger.info("Pipeline completado exitosamente")
            logger.info(f"Salida: {result.stdout[-500:]}")  # Últimas 500 chars
        else:
            logger.error(f"Pipeline falló con código {result.returncode}")
            logger.error(f"Error: {result.stderr[-500:]}")
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        logger.error("Pipeline excedió el tiempo límite de 1 hora")
        return False
    
    except Exception as e:
        logger.error(f"Error ejecutando pipeline: {e}", exc_info=True)
        return False


def ejecutar_entrenamiento():
    """Ejecuta solo el entrenamiento de modelos."""
    logger.info("="*70)
    logger.info("Iniciando entrenamiento programado")
    logger.info("="*70)
    
    try:
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "main.py", "--train"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=7200  # 2 horas máximo
        )
        
        if result.returncode == 0:
            logger.info("Entrenamiento completado exitosamente")
        else:
            logger.error(f"Entrenamiento falló con código {result.returncode}")
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Error ejecutando entrenamiento: {e}", exc_info=True)
        return False


def ejecutar_recoleccion():
    """Ejecuta solo la recolección de datos."""
    logger.info("Iniciando recolección de datos programada")
    
    try:
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "main.py", "--collect"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos máximo
        )
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Error ejecutando recolección: {e}", exc_info=True)
        return False


def scheduler_simple():
    """
    Scheduler simple usando el módulo schedule.
    Ideal para desarrollo y pruebas.
    """
    try:
        import schedule
    except ImportError:
        logger.error("Módulo 'schedule' no instalado. Instala con: pip install schedule")
        return
    
    logger.info("Iniciando scheduler simple (schedule)")
    logger.info("Configuración:")
    
    # Configurar tareas programadas
    schedule_config = {
        "recoleccion_diaria": os.getenv("SCHEDULE_COLLECT_DAILY", "08:00"),
        "entrenamiento_semanal": os.getenv("SCHEDULE_TRAIN_WEEKLY", "Sunday 02:00"),
        "pipeline_mensual": os.getenv("SCHEDULE_PIPELINE_MONTHLY", "1st 03:00")
    }
    
    # Recolección diaria
    if schedule_config["recoleccion_diaria"]:
        schedule.every().day.at(schedule_config["recoleccion_diaria"]).do(ejecutar_recoleccion)
        logger.info(f"  - Recolección diaria: {schedule_config['recoleccion_diaria']}")
    
    # Entrenamiento semanal (domingos)
    if "Sunday" in schedule_config["entrenamiento_semanal"]:
        time_str = schedule_config["entrenamiento_semanal"].split()[1]
        schedule.every().sunday.at(time_str).do(ejecutar_entrenamiento)
        logger.info(f"  - Entrenamiento semanal: Domingos {time_str}")
    
    # Pipeline completo mensual (día 1)
    # Nota: schedule no soporta días del mes directamente, usar APScheduler para esto
    
    killer = GracefulKiller()
    
    logger.info("Scheduler iniciado. Esperando tareas programadas...")
    logger.info("Presiona Ctrl+C para detener")
    
    while not killer.kill_now:
        schedule.run_pending()
        time.sleep(60)  # Verificar cada minuto
    
    logger.info("Scheduler detenido")


def scheduler_apscheduler():
    """
    Scheduler avanzado usando APScheduler.
    Soporta cron expressions y más opciones.
    """
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("Módulo 'apscheduler' no instalado. Instala con: pip install apscheduler")
        return
    
    logger.info("Iniciando scheduler avanzado (APScheduler)")
    
    scheduler = BlockingScheduler()
    
    # Configuración desde variables de entorno
    # Formato cron: "minuto hora dia mes dia_semana"
    
    # Recolección diaria a las 8:00 AM
    collect_cron = os.getenv("SCHEDULE_COLLECT_CRON", "0 8 * * *")
    scheduler.add_job(
        ejecutar_recoleccion,
        CronTrigger.from_crontab(collect_cron),
        id='recoleccion_diaria',
        name='Recolección de datos diaria',
        replace_existing=True
    )
    logger.info(f"  - Recolección: {collect_cron}")
    
    # Entrenamiento semanal (domingos a las 2:00 AM)
    train_cron = os.getenv("SCHEDULE_TRAIN_CRON", "0 2 * * 0")
    scheduler.add_job(
        ejecutar_entrenamiento,
        CronTrigger.from_crontab(train_cron),
        id='entrenamiento_semanal',
        name='Entrenamiento semanal de modelos',
        replace_existing=True
    )
    logger.info(f"  - Entrenamiento: {train_cron}")
    
    # Pipeline completo mensual (día 1 a las 3:00 AM)
    pipeline_cron = os.getenv("SCHEDULE_PIPELINE_CRON", "0 3 1 * *")
    scheduler.add_job(
        ejecutar_pipeline_completo,
        CronTrigger.from_crontab(pipeline_cron),
        id='pipeline_mensual',
        name='Pipeline completo mensual',
        replace_existing=True
    )
    logger.info(f"  - Pipeline completo: {pipeline_cron}")
    
    logger.info("Scheduler iniciado. Tareas programadas:")
    scheduler.print_jobs()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido por usuario")
        scheduler.shutdown()


def generar_crontab():
    """
    Genera un archivo crontab para usar con cron de Linux.
    """
    logger.info("Generando archivo crontab...")
    
    python_path = sys.executable
    project_path = ROOT_DIR
    
    crontab_content = f"""# Crontab para Sistema de Predicción de Lotería
# Generado automáticamente - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Variables de entorno
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
PYTHONPATH={project_path}

# Recolección de datos diaria a las 8:00 AM
0 8 * * * cd {project_path} && {python_path} main.py --collect >> {project_path}/logs/cron.log 2>&1

# Entrenamiento semanal (domingos a las 2:00 AM)
0 2 * * 0 cd {project_path} && {python_path} main.py --train >> {project_path}/logs/cron.log 2>&1

# Pipeline completo mensual (día 1 a las 3:00 AM)
0 3 1 * * cd {project_path} && {python_path} index.py >> {project_path}/logs/cron.log 2>&1

# Limpieza de logs antiguos (cada domingo a las 4:00 AM)
0 4 * * 0 find {project_path}/logs -name "*.log" -mtime +30 -delete

"""
    
    crontab_file = ROOT_DIR / "crontab.txt"
    with open(crontab_file, 'w') as f:
        f.write(crontab_content)
    
    logger.info(f"Archivo crontab generado: {crontab_file}")
    logger.info("\nPara instalar en Linux/Mac:")
    logger.info(f"  crontab {crontab_file}")
    logger.info("\nPara ver crontab actual:")
    logger.info("  crontab -l")
    logger.info("\nPara editar crontab:")
    logger.info("  crontab -e")
    
    return crontab_file


def main():
    """Función principal del scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scheduler para entrenamientos automáticos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Scheduler simple (schedule)
  python scripts/scheduler.py --mode simple

  # Scheduler avanzado (APScheduler)
  python scripts/scheduler.py --mode apscheduler

  # Generar crontab para Linux/Mac
  python scripts/scheduler.py --mode crontab

  # Ejecutar tarea inmediatamente (testing)
  python scripts/scheduler.py --run pipeline
  python scripts/scheduler.py --run train
  python scripts/scheduler.py --run collect

Variables de entorno para configuración:

  # Schedule simple
  SCHEDULE_COLLECT_DAILY=08:00
  SCHEDULE_TRAIN_WEEKLY="Sunday 02:00"

  # APScheduler (formato cron)
  SCHEDULE_COLLECT_CRON="0 8 * * *"
  SCHEDULE_TRAIN_CRON="0 2 * * 0"
  SCHEDULE_PIPELINE_CRON="0 3 1 * *"
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['simple', 'apscheduler', 'crontab'],
        default='simple',
        help='Modo de scheduler a usar'
    )
    
    parser.add_argument(
        '--run',
        choices=['pipeline', 'train', 'collect'],
        help='Ejecutar tarea inmediatamente (para testing)'
    )
    
    args = parser.parse_args()
    
    # Ejecutar tarea inmediata si se especifica
    if args.run:
        logger.info(f"Ejecutando tarea: {args.run}")
        if args.run == 'pipeline':
            ejecutar_pipeline_completo()
        elif args.run == 'train':
            ejecutar_entrenamiento()
        elif args.run == 'collect':
            ejecutar_recoleccion()
        return
    
    # Iniciar scheduler según modo
    if args.mode == 'simple':
        scheduler_simple()
    elif args.mode == 'apscheduler':
        scheduler_apscheduler()
    elif args.mode == 'crontab':
        generar_crontab()


if __name__ == "__main__":
    main()
