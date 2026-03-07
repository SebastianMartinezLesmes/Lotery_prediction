"""
Visualización del progreso de entrenamiento de modelos.
Proporciona barras de progreso, gráficos y reportes en tiempo real.
"""
import sys
import time
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

from src.core.config import settings


class TrainingProgressBar:
    """Barra de progreso mejorada para entrenamiento."""
    
    def __init__(self, total: int, width: int = 50):
        """
        Inicializa la barra de progreso.
        
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
        series_f1: float
    ) -> None:
        """
        Actualiza la barra de progreso.
        
        Args:
            iteration: Número de iteración actual
            result_acc: Accuracy del modelo result
            series_acc: Accuracy del modelo series
            result_f1: F1-score del modelo result
            series_f1: F1-score del modelo series
        """
        self.current = iteration
        
        # Detectar mejoras
        improved = False
        if result_acc > self.best_result_acc:
            self.best_result_acc = result_acc
            improved = True
        if series_acc > self.best_series_acc:
            self.best_series_acc = series_acc
            improved = True
        
        if improved:
            self.improvements += 1
        
        # Calcular progreso
        progress = iteration / self.total
        
        # Calcular tiempo
        elapsed = time.time() - self.start_time
        if iteration > 0:
            avg_time = elapsed / iteration
            remaining = avg_time * (self.total - iteration)
        else:
            remaining = 0
        
        # Formatear tiempo
        elapsed_str = self._format_time(elapsed)
        remaining_str = self._format_time(remaining)
        
        # Indicador de mejora
        improvement_icon = "**" if improved else "  "
        
        # Construir línea de progreso (SIN BARRA)
        line = (
            f"\r{improvement_icon} {iteration}/{self.total} ({progress*100:.1f}%) | "
            f"Time: {elapsed_str}/{remaining_str} | "
            f"Result: {result_acc:.4f} ({result_f1:.4f}) | "
            f"Series: {series_acc:.4f} ({series_f1:.4f}) | "
            f"Best: R={self.best_result_acc:.4f} S={self.best_series_acc:.4f} | "
            f"Improvements: {self.improvements}"
        )
        
        sys.stdout.write(line)
        sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Formatea segundos a formato legible."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def finish(self, success: bool = True) -> None:
        """Finaliza la barra de progreso."""
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        if success:
            print(f"\nEntrenamiento completado en {elapsed_str}")
            print(f"   Mejores resultados: Result={self.best_result_acc:.4f}, Series={self.best_series_acc:.4f}")
            print(f"   Total de mejoras: {self.improvements}")
        else:
            print(f"\nEntrenamiento detenido en {elapsed_str}")


class TrainingLogger:
    """Logger de métricas de entrenamiento."""
    
    def __init__(self, lottery_name: str, log_dir: str = "logs"):
        """
        Inicializa el logger.
        
        Args:
            lottery_name: Nombre de la lotería
            log_dir: Directorio para guardar logs
        """
        self.lottery_name = lottery_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.history: Dict[str, List] = {
            "attempts": [],
            "result_acc": [],
            "series_acc": [],
            "result_f1": [],
            "series_f1": [],
            "timestamps": []
        }
        
        self.start_time = datetime.now()
    
    def log_iteration(
        self,
        iteration: int,
        result_acc: float,
        series_acc: float,
        result_f1: float,
        series_f1: float
    ) -> None:
        """Registra una iteración."""
        self.history["attempts"].append(iteration)
        self.history["result_acc"].append(result_acc)
        self.history["series_acc"].append(series_acc)
        self.history["result_f1"].append(result_f1)
        self.history["series_f1"].append(series_f1)
        self.history["timestamps"].append(datetime.now().isoformat())
    
    def save(self, max_files_per_lottery: Optional[int] = None) -> str:
        """
        Guarda el historial de entrenamiento y limpia archivos antiguos.
        
        Args:
            max_files_per_lottery: Número máximo de archivos a mantener por lotería 
                                   (usa settings.MAX_TRAINING_LOGS si no se especifica)
        
        Returns:
            Ruta del archivo guardado
        """
        if max_files_per_lottery is None:
            max_files_per_lottery = settings.TRAINING_CONFIGURE["max_training_logs"],
        
        filename = f"training_{self.lottery_name}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename
        
        data = {
            "lottery": self.lottery_name,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_iterations": len(self.history["attempts"]),
            "best_result_acc": max(self.history["result_acc"]) if self.history["result_acc"] else 0,
            "best_series_acc": max(self.history["series_acc"]) if self.history["series_acc"] else 0,
            "history": self.history
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Limpiar archivos antiguos de esta lotería
        self._cleanup_old_files(max_files_per_lottery)
        
        return str(filepath)
    
    def _cleanup_old_files(self, max_files: int) -> None:
        """
        Mantiene los N mejores entrenamientos según accuracy combinada.
        
        Estrategia:
        - Ordena todos los archivos por score combinado (best_result_acc + best_series_acc) / 2
        - Mantiene los N mejores (mayor score)
        - Elimina el resto
        - El mejor se considera candidato a .pkl
        - Los demás son experimentales
        
        Args:
            max_files: Número máximo de archivos a mantener (los N mejores)
        """
        # Buscar todos los archivos de entrenamiento de esta lotería
        pattern = f"training_{self.lottery_name}_*.json"
        training_files = list(self.log_dir.glob(pattern))
        
        # Si hay más archivos que el máximo permitido
        if len(training_files) > max_files:
            # Leer todos los archivos y calcular scores
            files_with_scores = []
            for file_path in training_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Calcular score combinado (promedio de ambos modelos)
                        combined_score = (
                            data.get('best_result_acc', 0) + 
                            data.get('best_series_acc', 0)
                        ) / 2
                        files_with_scores.append({
                            'path': file_path,
                            'score': combined_score,
                            'result_acc': data.get('best_result_acc', 0),
                            'series_acc': data.get('best_series_acc', 0)
                        })
                except Exception as e:
                    # Si no se puede leer, usar score 0
                    files_with_scores.append({
                        'path': file_path,
                        'score': 0,
                        'result_acc': 0,
                        'series_acc': 0
                    })
            
            # Ordenar por score (mayor a menor)
            files_with_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Mantener los N mejores
            files_to_keep = set(f['path'] for f in files_with_scores[:max_files])
            
            # Mostrar los mejores que se mantienen
            print(f"\n   📊 Manteniendo Top {max_files} entrenamientos:")
            for i, file_info in enumerate(files_with_scores[:max_files], 1):
                role = "MEJOR (candidato .pkl)" if i == 1 else "EXPERIMENTAL"
                marker = "🏆" if i == 1 else "🧪"
                print(f"      {marker} #{i} [{role}]: {file_info['path'].name}")
                print(f"         Score={file_info['score']:.4f} (R={file_info['result_acc']:.4f}, S={file_info['series_acc']:.4f})")
            
            # Eliminar los archivos que no están en el top N
            files_to_delete = files_with_scores[max_files:]
            if files_to_delete:
                print(f"\n   🗑️  Eliminando {len(files_to_delete)} archivo(s) antiguo(s):")
                for file_info in files_to_delete:
                    try:
                        file_info['path'].unlink()
                        print(f"      ❌ {file_info['path'].name} (Score={file_info['score']:.4f})")
                    except Exception as e:
                        print(f"      ⚠️ No se pudo eliminar {file_info['path'].name}: {e}")
    
    def generate_summary(self) -> str:
        """Genera un resumen del entrenamiento."""
        if not self.history["attempts"]:
            return "No hay datos de entrenamiento"
        
        total_iterations = len(self.history["attempts"])
        best_result_acc = max(self.history["result_acc"])
        best_series_acc = max(self.history["series_acc"])
        avg_result_acc = sum(self.history["result_acc"]) / total_iterations
        avg_series_acc = sum(self.history["series_acc"]) / total_iterations
        
        duration = datetime.now() - self.start_time
        
        summary = f"""
================================================================
           RESUMEN DE ENTRENAMIENTO - {self.lottery_name.upper()}           
================================================================

Estadisticas Generales:
   * Total de iteraciones: {total_iterations}
   * Duracion: {duration}
   * Iteraciones/segundo: {total_iterations / duration.total_seconds():.2f}

Modelo Result (Numeros):
   * Mejor Accuracy: {best_result_acc:.4f}
   * Promedio Accuracy: {avg_result_acc:.4f}
   * Mejor F1-Score: {max(self.history["result_f1"]):.4f}

Modelo Series (Simbolos):
   * Mejor Accuracy: {best_series_acc:.4f}
   * Promedio Accuracy: {avg_series_acc:.4f}
   * Mejor F1-Score: {max(self.history["series_f1"]):.4f}

Progreso:
   * Primera iteracion: Result={self.history["result_acc"][0]:.4f}, Series={self.history["series_acc"][0]:.4f}
   * Ultima iteracion: Result={self.history["result_acc"][-1]:.4f}, Series={self.history["series_acc"][-1]:.4f}
   * Mejora Result: {(best_result_acc - self.history["result_acc"][0]):.4f}
   * Mejora Series: {(best_series_acc - self.history["series_acc"][0]):.4f}

================================================================
"""
        return summary


class TrainingVisualizer:
    """Visualizador completo de entrenamiento."""
    
    def __init__(
        self,
        lottery_name: str,
        total_iterations: int,
        enable_progress_bar: bool = True,
        enable_logging: bool = True,
        log_dir: str = "logs"
    ):
        """
        Inicializa el visualizador.
        
        Args:
            lottery_name: Nombre de la lotería
            total_iterations: Número total de iteraciones
            enable_progress_bar: Habilitar barra de progreso
            enable_logging: Habilitar logging de métricas
            log_dir: Directorio para logs
        """
        self.lottery_name = lottery_name
        self.total_iterations = total_iterations
        
        self.progress_bar = TrainingProgressBar(total_iterations) if enable_progress_bar else None
        self.logger = TrainingLogger(lottery_name, log_dir) if enable_logging else None
        
        self.start_time = time.time()
    
    def update(
        self,
        iteration: int,
        result_acc: float,
        series_acc: float,
        result_f1: float,
        series_f1: float
    ) -> None:
        """
        Actualiza la visualización.
        
        Args:
            iteration: Número de iteración
            result_acc: Accuracy del modelo result
            series_acc: Accuracy del modelo series
            result_f1: F1-score del modelo result
            series_f1: F1-score del modelo series
        """
        if self.progress_bar:
            self.progress_bar.update(iteration, result_acc, series_acc, result_f1, series_f1)
        
        if self.logger:
            self.logger.log_iteration(iteration, result_acc, series_acc, result_f1, series_f1)
    
    def finish(self, success: bool = True) -> Optional[str]:
        """
        Finaliza la visualización.
        
        Args:
            success: Si el entrenamiento fue exitoso
        
        Returns:
            Ruta del archivo de log guardado (si logging está habilitado)
        """
        if self.progress_bar:
            self.progress_bar.finish(success)
        
        log_path = None
        if self.logger:
            log_path = self.logger.save()
            print(f"\nHistorial guardado en: {log_path}")
            
            # Mostrar resumen
            print(self.logger.generate_summary())
        
        return log_path
    
    def get_history(self) -> Optional[Dict]:
        """Obtiene el historial de entrenamiento."""
        return self.logger.history if self.logger else None


def create_training_report(log_file: str) -> str:
    """
    Crea un reporte HTML del entrenamiento.
    
    Args:
        log_file: Ruta al archivo JSON de log
    
    Returns:
        Ruta del archivo HTML generado
    """
    with open(log_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Reporte de Entrenamiento - {data['lottery']}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Reporte de Entrenamiento</h1>
        <h2>{data['lottery'].upper()}</h2>
        <p>Inicio: {data['start_time']} | Fin: {data['end_time']}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{data['total_iterations']}</div>
            <div class="stat-label">Iteraciones Totales</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data['best_result_acc']:.4f}</div>
            <div class="stat-label">Mejor Accuracy (Result)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{data['best_series_acc']:.4f}</div>
            <div class="stat-label">Mejor Accuracy (Series)</div>
        </div>
    </div>
    
    <div class="chart">
        <h3>📈 Progreso de Entrenamiento</h3>
        <p>Ver archivo JSON para datos completos: {log_file}</p>
    </div>
</body>
</html>
"""
    
    html_file = log_file.replace('.json', '.html')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_file
