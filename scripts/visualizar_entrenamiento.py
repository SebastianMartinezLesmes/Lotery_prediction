"""
Script para visualizar el historial de entrenamientos guardados.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict
import argparse


def listar_entrenamientos(log_dir: str = "logs") -> List[Path]:
    """Lista todos los archivos de entrenamiento."""
    log_path = Path(log_dir)
    if not log_path.exists():
        return []
    
    return sorted(log_path.glob("training_*.json"), reverse=True)


def mostrar_resumen(log_file: Path) -> None:
    """Muestra un resumen de un entrenamiento."""
    with open(log_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*70)
    print(f"📊 ENTRENAMIENTO: {data['lottery'].upper()}")
    print("="*70)
    
    print(f"\n⏰ Tiempo:")
    print(f"   Inicio: {data['start_time']}")
    print(f"   Fin:    {data['end_time']}")
    
    print(f"\n📈 Estadísticas:")
    print(f"   Total de iteraciones: {data['total_iterations']}")
    print(f"   Mejor Accuracy (Result): {data['best_result_acc']:.4f}")
    print(f"   Mejor Accuracy (Series): {data['best_series_acc']:.4f}")
    
    history = data['history']
    if history['result_acc']:
        print(f"\n📊 Progreso:")
        print(f"   Primera iteración:")
        print(f"      Result: {history['result_acc'][0]:.4f}")
        print(f"      Series: {history['series_acc'][0]:.4f}")
        print(f"   Última iteración:")
        print(f"      Result: {history['result_acc'][-1]:.4f}")
        print(f"      Series: {history['series_acc'][-1]:.4f}")
        print(f"   Mejora:")
        print(f"      Result: +{(data['best_result_acc'] - history['result_acc'][0]):.4f}")
        print(f"      Series: +{(data['best_series_acc'] - history['series_acc'][0]):.4f}")
    
    print("\n" + "="*70)


def mostrar_grafico_ascii(data: Dict) -> None:
    """Muestra un gráfico ASCII del progreso."""
    history = data['history']
    result_acc = history['result_acc']
    series_acc = history['series_acc']
    
    if not result_acc:
        print("No hay datos para graficar")
        return
    
    print("\n📈 GRÁFICO DE PROGRESO (Accuracy)")
    print("="*70)
    
    # Tomar muestras para el gráfico (máximo 50 puntos)
    step = max(1, len(result_acc) // 50)
    sampled_result = result_acc[::step]
    sampled_series = series_acc[::step]
    sampled_attempts = history['attempts'][::step]
    
    # Escalar valores a altura de 20 líneas
    height = 20
    min_val = 0.0
    max_val = 1.0
    
    def scale(val):
        return int((val - min_val) / (max_val - min_val) * height)
    
    # Crear gráfico
    for y in range(height, -1, -1):
        line = f"{(y/height):.2f} |"
        
        for i in range(len(sampled_result)):
            result_y = scale(sampled_result[i])
            series_y = scale(sampled_series[i])
            
            if result_y == y and series_y == y:
                line += "●"
            elif result_y == y:
                line += "R"
            elif series_y == y:
                line += "S"
            else:
                line += " "
        
        print(line)
    
    # Eje X
    print("     +" + "-" * len(sampled_result))
    print(f"      Iteraciones: {sampled_attempts[0]} → {sampled_attempts[-1]}")
    print("\n     Leyenda: R=Result, S=Series, ●=Ambos")


def comparar_entrenamientos(log_files: List[Path]) -> None:
    """Compara múltiples entrenamientos."""
    if len(log_files) < 2:
        print("Se necesitan al menos 2 entrenamientos para comparar")
        return
    
    print("\n" + "="*70)
    print("📊 COMPARACIÓN DE ENTRENAMIENTOS")
    print("="*70)
    
    print(f"\n{'Lotería':<20} {'Iteraciones':<15} {'Best Result':<15} {'Best Series':<15}")
    print("-"*70)
    
    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        lottery = data['lottery'][:18]
        iterations = data['total_iterations']
        best_result = data['best_result_acc']
        best_series = data['best_series_acc']
        
        print(f"{lottery:<20} {iterations:<15} {best_result:<15.4f} {best_series:<15.4f}")
    
    print("="*70)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Visualizador de entrenamientos de modelos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python visualizar_entrenamiento.py                    # Listar todos
  python visualizar_entrenamiento.py --latest           # Ver el más reciente
  python visualizar_entrenamiento.py --file training_*.json  # Ver específico
  python visualizar_entrenamiento.py --compare          # Comparar todos
  python visualizar_entrenamiento.py --graph            # Ver gráfico
        """
    )
    
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Mostrar el entrenamiento más reciente'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Archivo específico de entrenamiento'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Comparar todos los entrenamientos'
    )
    
    parser.add_argument(
        '--graph',
        action='store_true',
        help='Mostrar gráfico ASCII del progreso'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Directorio de logs (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Listar entrenamientos disponibles
    entrenamientos = listar_entrenamientos(args.log_dir)
    
    if not entrenamientos:
        print(f"❌ No se encontraron entrenamientos en {args.log_dir}/")
        print("\nPara generar entrenamientos, ejecuta:")
        print("  python -m src.utils.training")
        return 1
    
    # Mostrar archivo específico
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Archivo no encontrado: {args.file}")
            return 1
        
        mostrar_resumen(file_path)
        
        if args.graph:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            mostrar_grafico_ascii(data)
        
        return 0
    
    # Mostrar el más reciente
    if args.latest:
        mostrar_resumen(entrenamientos[0])
        
        if args.graph:
            with open(entrenamientos[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            mostrar_grafico_ascii(data)
        
        return 0
    
    # Comparar todos
    if args.compare:
        comparar_entrenamientos(entrenamientos)
        return 0
    
    # Listar todos por defecto
    print("\n📁 ENTRENAMIENTOS DISPONIBLES")
    print("="*70)
    
    for i, log_file in enumerate(entrenamientos, 1):
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n{i}. {log_file.name}")
        print(f"   Lotería: {data['lottery']}")
        print(f"   Fecha: {data['start_time']}")
        print(f"   Iteraciones: {data['total_iterations']}")
        print(f"   Best Accuracy: Result={data['best_result_acc']:.4f}, Series={data['best_series_acc']:.4f}")
    
    print("\n" + "="*70)
    print("\nPara ver detalles, usa:")
    print("  python visualizar_entrenamiento.py --latest")
    print("  python visualizar_entrenamiento.py --file <archivo>")
    print("  python visualizar_entrenamiento.py --compare")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
