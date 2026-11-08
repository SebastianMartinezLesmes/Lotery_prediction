"""
Visualización del progreso de entrenamiento de modelos.
Proporciona barras de progreso y reportes en tiempo real por consola.

POLÍTICA: este módulo no escribe ningún archivo en disco.
Toda la salida va a stdout. Los datos de historial solo existen en memoria
durante la sesión de entrenamiento.
"""
import sys
import time

from datetime import datetime
from src.core.config import settings
from typing import Dict, List, Optional


class TrainingProgressBar:
    """Barra de progreso mejorada para entrenamiento."""

    def __init__(self, total: int, width: int = 50):
        """
        Args:
            total: Número total de iteraciones
            width: Ancho de la barra en caracteres
        """
        self.total = total
        self.width = width
        self.current = 0
        self.start_time = time.time()
        self.best_result_acc = 0.0
        self.best_series_acc = 0.0
        self.improvements = 0

    def update(
        self,
        iteration: int,
        result_acc: float,
        series_acc: float,
        result_f1: float,
        series_f1: float,
    ) -> None:
        """Actualiza la barra de progreso en consola."""
        self.current = iteration

        improved = False
        if result_acc > self.best_result_acc:
            self.best_result_acc = result_acc
            improved = True
        if series_acc > self.best_series_acc:
            self.best_series_acc = series_acc
            improved = True

        if improved:
            self.improvements += 1

        progress = iteration / self.total
        elapsed = time.time() - self.start_time
        if iteration > 0:
            remaining = (elapsed / iteration) * (self.total - iteration)
        else:
            remaining = 0

        improvement_icon = "**" if improved else "  "

        line = (
            f"\n \r{improvement_icon} {iteration}/{self.total} ({progress*100:.1f}%) | "
            f"Time: {self._format_time(remaining)} | "
            f"Result: {result_f1:.4f} | "
            f"Series: {series_f1:.4f} | "
            f"Best: R={self.best_result_acc:.4f} S={self.best_series_acc:.4f} | "
            f"Improvements: {self.improvements} \n"
        )

        sys.stdout.write(line)
        sys.stdout.flush()

    def _format_time(self, seconds: float) -> str:
        """Formatea segundos a formato legible."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"

    def finish(self, success: bool = True) -> None:
        """Finaliza la barra de progreso."""
        elapsed = time.time() - self.start_time
        if success:
            print(f"\nEntrenamiento completado en {self._format_time(elapsed)}")
            print(f"   Mejores resultados: Result={self.best_result_acc:.4f}, Series={self.best_series_acc:.4f}")
            print(f"   Total de mejoras: {self.improvements}")
        else:
            print(f"\nEntrenamiento detenido en {self._format_time(elapsed)}")


class TrainingLogger:
    """
    Acumula métricas de entrenamiento en memoria y las imprime a consola.

    No escribe ningún archivo en disco. generate_summary() imprime el resumen
    directamente a stdout; get_history() retorna los datos en memoria para uso
    programático dentro de la misma sesión.
    """

    def __init__(self, lottery_name: str, log_dir: str = "logs"):
        """
        Args:
            lottery_name: Nombre de la lotería.
            log_dir:      Ignorado — se mantiene la firma por compatibilidad con
                          código existente que pasa este argumento.
        """
        self.lottery_name = lottery_name
        # log_dir ignorado intencionalmente: no se escribe en disco.

        self.history: Dict[str, List] = {
            "attempts": [],
            "result_acc": [],
            "series_acc": [],
            "result_f1": [],
            "series_f1": [],
            "timestamps": [],
        }
        self.start_time = datetime.now()

    def log_iteration(
        self,
        iteration: int,
        result_acc: float,
        series_acc: float,
        result_f1: float,
        series_f1: float,
    ) -> None:
        """Registra una iteración en memoria."""
        self.history["attempts"].append(iteration)
        self.history["result_acc"].append(result_acc)
        self.history["series_acc"].append(series_acc)
        self.history["result_f1"].append(result_f1)
        self.history["series_f1"].append(series_f1)
        self.history["timestamps"].append(datetime.now().isoformat())

    def save(self, max_files_per_lottery: Optional[int] = None) -> str:
        """
        Imprime el resumen a consola (no escribe archivos).

        La firma original retornaba la ruta del archivo guardado; ahora retorna
        una cadena vacía para mantener compatibilidad con código que usa el valor
        de retorno sin romper nada.
        """
        print(self.generate_summary())
        return ""

    def generate_summary(self) -> str:
        """Genera y retorna el resumen del entrenamiento como texto."""
        if not self.history["attempts"]:
            return "No hay datos de entrenamiento"

        total_iterations = len(self.history["attempts"])
        best_result_acc = max(self.history["result_acc"])
        best_series_acc = max(self.history["series_acc"])
        avg_result_acc = sum(self.history["result_acc"]) / total_iterations
        avg_series_acc = sum(self.history["series_acc"]) / total_iterations
        duration = datetime.now() - self.start_time

        return f"""
================================================================
           RESUMEN DE ENTRENAMIENTO - {self.lottery_name.upper()}
================================================================

Estadisticas Generales:
   * Total de iteraciones: {total_iterations}
   * Duracion: {duration}
   * Iteraciones/segundo: {total_iterations / max(duration.total_seconds(), 0.001):.2f}

Modelo Result (Numeros):
   * Mejor Accuracy: {best_result_acc:.4f}
   * Promedio Accuracy: {avg_result_acc:.4f}
   * Mejor F1-Score: {max(self.history["result_f1"]) if self.history["result_f1"] else 0:.4f}

Modelo Series (Simbolos):
   * Mejor Accuracy: {best_series_acc:.4f}
   * Promedio Accuracy: {avg_series_acc:.4f}
   * Mejor F1-Score: {max(self.history["series_f1"]) if self.history["series_f1"] else 0:.4f}

Progreso:
   * Primera iteracion: Result={self.history["result_acc"][0]:.4f}, Series={self.history["series_acc"][0]:.4f}
   * Ultima iteracion:  Result={self.history["result_acc"][-1]:.4f}, Series={self.history["series_acc"][-1]:.4f}
   * Mejora Result: {(best_result_acc - self.history["result_acc"][0]):.4f}
   * Mejora Series: {(best_series_acc - self.history["series_acc"][0]):.4f}

================================================================
"""


class TrainingVisualizer:
    """Visualizador completo de entrenamiento — solo consola, sin archivos."""

    def __init__(
        self,
        lottery_name: str,
        total_iterations: int,
        enable_progress_bar: bool = True,
        enable_logging: bool = True,
        log_dir: str = "logs",   # ignorado, se mantiene por compatibilidad
    ):
        """
        Args:
            lottery_name:        Nombre de la lotería.
            total_iterations:    Número total de iteraciones.
            enable_progress_bar: Habilitar barra de progreso en consola.
            enable_logging:      Habilitar acumulación de métricas y summary final.
            log_dir:             Ignorado — no se escribe en disco.
        """
        self.lottery_name = lottery_name
        self.total_iterations = total_iterations

        self.progress_bar = TrainingProgressBar(total_iterations) if enable_progress_bar else None
        self.logger = TrainingLogger(lottery_name) if enable_logging else None

        self.start_time = time.time()

    def update(
        self,
        iteration: int,
        result_acc: float,
        series_acc: float,
        result_f1: float,
        series_f1: float,
    ) -> None:
        """Actualiza la barra de progreso y acumula métricas."""
        if self.progress_bar:
            self.progress_bar.update(iteration, result_acc, series_acc, result_f1, series_f1)
        if self.logger:
            self.logger.log_iteration(iteration, result_acc, series_acc, result_f1, series_f1)

    def finish(self, success: bool = True) -> Optional[str]:
        """
        Finaliza la visualización e imprime el resumen a consola.

        Returns:
            Cadena vacía (antes retornaba la ruta del archivo de log).
            Se mantiene el tipo de retorno para compatibilidad.
        """
        if self.progress_bar:
            self.progress_bar.finish(success)

        if self.logger:
            print(self.logger.generate_summary())

        return ""

    def get_history(self) -> Optional[Dict]:
        """Retorna el historial de métricas en memoria."""
        return self.logger.history if self.logger else None
