"""
Punto de entrada principal del sistema de predicción de lotería.
Ejecuta el pipeline completo: dependencias -> datos -> predicción.
"""
import subprocess
import sys
from typing import List, Tuple, Optional
from pathlib import Path

from src.core.logger import get_main_logger
from src.core.exceptions import LotteryPredictionError
from src.utils.drop_cache import eliminar_pycache

logger = get_main_logger()


class ScriptExecutor:
    """Ejecutor de scripts del pipeline."""
    
    def __init__(self, scripts: List[Tuple[str, str]]):
        """
        Inicializa el ejecutor.
        
        Args:
            scripts: Lista de tuplas (nombre_amigable, ruta_script)
        """
        self.scripts = scripts
        self.total = len(scripts)
        self.exitosos = 0
    
    def ejecutar_script(self, nombre_amigable: str, ruta_script: str) -> bool:
        """
        Ejecuta un script individual del pipeline.
        
        Args:
            nombre_amigable: Nombre descriptivo del script
            ruta_script: Ruta relativa al script
        
        Returns:
            True si el script se ejecutó exitosamente, False en caso contrario
        """
        logger.info(f"▶ Ejecutando: {nombre_amigable} ({ruta_script})")
        print(f">> {nombre_amigable}...")
        
        try:
            # Validar que el archivo existe
            script_path = Path(ruta_script)
            if not script_path.exists():
                raise FileNotFoundError(f"Script no encontrado: {ruta_script}")
            
            # Convertir ruta a módulo Python
            modulo = ruta_script.replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # Ejecutar como módulo
            result = subprocess.run(
                [sys.executable, "-m", modulo],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            logger.info(f"Completado: {nombre_amigable}")
            print(f"OK {nombre_amigable} completado.\n")
            return True
        
        except subprocess.CalledProcessError as e:
            error_msg = f"Error en ejecución: {e.stderr if e.stderr else str(e)}"
            logger.error(f"Falló: {nombre_amigable} - {error_msg}")
            print(f"ERROR en {nombre_amigable}.")
            print(f"   Detalles: {error_msg[:200]}")
            print(f"   Ver log completo: logs/log_loteria.log\n")
            return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout: {nombre_amigable} excedió el tiempo límite")
            print(f"TIMEOUT: {nombre_amigable} excedió el tiempo límite.\n")
            return False
        
        except FileNotFoundError as e:
            logger.error(f"Archivo no encontrado: {e}")
            print(f"ERROR: {e}\n")
            return False
        
        except Exception as e:
            logger.error(f"Error inesperado en {nombre_amigable}: {e}", exc_info=True)
            print(f"ERROR inesperado en {nombre_amigable}: {e}\n")
            return False
    
    def ejecutar_pipeline(self, stop_on_error: bool = True) -> int:
        """
        Ejecuta todos los scripts del pipeline.
        
        Args:
            stop_on_error: Si True, detiene la ejecución al primer error
        
        Returns:
            Número de scripts ejecutados exitosamente
        """
        print(">> INICIO DE EJECUCIÓN DEL SISTEMA DE LOTERÍA")
        print("-" * 50)
        logger.info("=" * 50)
        logger.info("Iniciando pipeline de ejecución")
        logger.info("=" * 50)
        
        for nombre, ruta in self.scripts:
            if self.ejecutar_script(nombre, ruta):
                self.exitosos += 1
            else:
                if stop_on_error:
                    logger.warning("Pipeline detenido por error")
                    break
        
        return self.exitosos
    
    def mostrar_resumen(self) -> None:
        """Muestra el resumen de ejecución."""
        print("\n== RESUMEN FINAL")
        print("-" * 50)
        print(f"OK Scripts exitosos: {self.exitosos}/{self.total}")
        print(f"   Registro detallado: logs/log_loteria.log")
        
        if self.exitosos == self.total:
            print(">> Pipeline completado exitosamente")
            logger.info("Pipeline completado exitosamente")
        else:
            print(f"!! Pipeline incompleto: {self.total - self.exitosos} script(s) fallaron")
            logger.warning(f"Pipeline incompleto: {self.exitosos}/{self.total}")
        
        print("-" * 50)


def limpiar_cache() -> None:
    """Limpia archivos de caché de Python."""
    print("\nLimpiando cachés (__pycache__)...")
    try:
        eliminar_pycache()
        logger.info("Caché limpiado exitosamente")
    except Exception as e:
        logger.error(f"Error al limpiar caché: {e}")
        print(f"!! Error al limpiar caché: {e}")


def mostrar_resultados_prediccion() -> None:
    """Muestra los resultados de las predicciones más recientes."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    results_path = Path("data/results.json")
    
    if not results_path.exists():
        print("\n!! No se encontraron resultados de predicción")
        return
    
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            resultados = json.load(f)
        
        if not resultados:
            print("\n!! No hay resultados disponibles")
            return
        
        # Agrupar por lotería y obtener el más reciente de cada una
        loterias_recientes = {}
        for resultado in resultados:
            loteria = resultado['resultado']['loteria']
            timestamp = datetime.fromisoformat(resultado['timestamp'])
            
            if loteria not in loterias_recientes or timestamp > loterias_recientes[loteria]['timestamp']:
                loterias_recientes[loteria] = {
                    'timestamp': timestamp,
                    'numero': resultado['resultado']['numero'],
                    'simbolo': resultado['resultado']['simbolo']
                }
        
        # Mostrar resultados
        print("\n" + "=" * 60)
        print("RESULTADOS DE PREDICCIÓN")
        print("=" * 60)
        
        for loteria, datos in sorted(loterias_recientes.items()):
            print(f"\nLoteria: {loteria}")
            print(f"  Serie: {datos['numero']}")
            print(f"  Simbolo: {datos['simbolo']}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        logger.error(f"Error al mostrar resultados: {e}")
        print(f"\n!! Error al mostrar resultados: {e}")


def main() -> int:
    """
    Función principal del sistema.
    
    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    # Definir pipeline de scripts
    scripts = [
        ("Dependencias", "src/utils/dependencies.py"),
        ("Recolección de Datos", "src/excel/read_excel.py"),
        ("Predicción", "src/utils/prediction.py")
    ]
    
    try:
        # Ejecutar pipeline
        executor = ScriptExecutor(scripts)
        exitosos = executor.ejecutar_pipeline(stop_on_error=True)
        
        # Mostrar resumen
        executor.mostrar_resumen()
        
        # Mostrar resultados de predicción si el pipeline fue exitoso
        if exitosos == len(scripts):
            mostrar_resultados_prediccion()
        
        # Limpiar caché
        limpiar_cache()
        
        # Retornar código de salida
        return 0 if exitosos == len(scripts) else 1
    
    except KeyboardInterrupt:
        logger.warning("Ejecución interrumpida por el usuario")
        print("\n!! Ejecución interrumpida por el usuario")
        return 1
    
    except Exception as e:
        logger.error(f"Error crítico en main: {e}", exc_info=True)
        print(f"\nERROR crítico: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
