"""
Script para ejecutar entrenamiento avanzado de ML.

Uso:
    python scripts/train_advanced.py
    python scripts/train_advanced.py --algorithm XGBoost
    python scripts/train_advanced.py --algorithm auto --search grid
"""

import sys
import argparse
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.training_advanced import main as train_advanced_main
from src.core.config import settings


def parse_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Entrenamiento avanzado de modelos de ML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/train_advanced.py
  python scripts/train_advanced.py --algorithm XGBoost
  python scripts/train_advanced.py --algorithm auto --search grid
  python scripts/train_advanced.py --no-feature-engineering
  python scripts/train_advanced.py --cv-folds 10 --search-iterations 50
        """
    )
    
    parser.add_argument(
        '--algorithm',
        type=str,
        default=settings.ML_ALGORITHM,
        choices=['RandomForest', 'XGBoost', 'LightGBM', 'auto'],
        help='Algoritmo de ML a usar (default: %(default)s)'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        default=settings.HYPERPARAMETER_SEARCH,
        choices=['grid', 'random', 'none'],
        help='Tipo de búsqueda de hiperparámetros (default: %(default)s)'
    )
    
    parser.add_argument(
        '--search-iterations',
        type=int,
        default=settings.SEARCH_ITERATIONS,
        help='Iteraciones para RandomizedSearchCV (default: %(default)s)'
    )
    
    parser.add_argument(
        '--cv-folds',
        type=int,
        default=settings.CV_FOLDS,
        help='Número de folds para validación cruzada (default: %(default)s)'
    )
    
    parser.add_argument(
        '--no-feature-engineering',
        action='store_true',
        help='Desactivar feature engineering avanzado'
    )
    
    return parser.parse_args()


def main():
    """Función principal."""
    args = parse_args()
    
    # Actualizar configuración con argumentos
    settings.ML_ALGORITHM = args.algorithm
    settings.HYPERPARAMETER_SEARCH = args.search
    settings.SEARCH_ITERATIONS = args.search_iterations
    settings.CV_FOLDS = args.cv_folds
    settings.ENABLE_FEATURE_ENGINEERING = not args.no_feature_engineering
    settings.USE_ADVANCED_ML = True
    
    print("="*70)
    print("ENTRENAMIENTO AVANZADO DE ML")
    print("="*70)
    print(f"\nParámetros:")
    print(f"   Algoritmo: {args.algorithm}")
    print(f"   Búsqueda: {args.search}")
    print(f"   Iteraciones búsqueda: {args.search_iterations}")
    print(f"   CV Folds: {args.cv_folds}")
    print(f"   Feature Engineering: {not args.no_feature_engineering}")
    print()
    
    # Ejecutar entrenamiento
    try:
        train_advanced_main()
    except KeyboardInterrupt:
        print("\n\n!! Entrenamiento interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n!! Error durante el entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
