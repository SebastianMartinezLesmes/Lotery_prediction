"""
Script de Entrenamiento Mejorado con Features Avanzadas.

Mejoras implementadas:
1. Features de frecuencia y patrones (números calientes/fríos)
2. Calibración de probabilidades
3. Optimización bayesiana de hiperparámetros

Uso:
    python scripts/train_enhanced.py
    python scripts/train_enhanced.py --lottery "ASTRO LUNA"
    python scripts/train_enhanced.py --algorithm XGBoost --iterations 100
    python scripts/train_enhanced.py --no-calibration
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
import argparse
import joblib
from datetime import datetime

from src.core.config import settings
from src.core.logger import LoggerManager
from src.utils.ml_enhanced import (
    EnhancedFeatureEngineer,
    CalibratedModelWrapper,
    BayesianOptimizer,
    BAYESIAN_AVAILABLE
)

logger = LoggerManager.get_logger("train_enhanced", "training_enhanced.log")


def main():
    parser = argparse.ArgumentParser(
        description="Entrenamiento Mejorado con Features Avanzadas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ENTRENAMIENTO MEJORADO

Mejoras implementadas:
  1. Features de frecuencia y patrones
     - Números calientes (más frecuentes últimamente)
     - Números fríos (menos frecuentes)
     - Intervalos entre apariciones
     - Tendencias de frecuencia
  
  2. Calibración de probabilidades
     - Mejora la confiabilidad de las predicciones
     - Permite saber cuándo confiar en una predicción
  
  3. Optimización bayesiana
     - Encuentra mejores hiperparámetros
     - Más eficiente que GridSearch

Ejemplos de uso:

  # Entrenar todas las loterías
  python scripts/train_enhanced.py

  # Lotería específica
  python scripts/train_enhanced.py --lottery "ASTRO LUNA"

  # Con algoritmo específico
  python scripts/train_enhanced.py --algorithm XGBoost

  # Más iteraciones de optimización
  python scripts/train_enhanced.py --iterations 100

  # Sin calibración (más rápido)
  python scripts/train_enhanced.py --no-calibration

  # Sin features de frecuencia (más rápido)
  python scripts/train_enhanced.py --no-frequency
        """
    )
    
    parser.add_argument(
        '--lottery',
        type=str,
        help='Lotería específica a entrenar'
    )
    
    parser.add_argument(
        '--algorithm',
        type=str,
        default='RandomForest',
        choices=['RandomForest', 'XGBoost', 'LightGBM'],
        help='Algoritmo a usar (default: RandomForest)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=50,
        help='Iteraciones de optimización bayesiana (default: 50)'
    )
    
    parser.add_argument(
        '--cv-folds',
        type=int,
        default=5,
        help='Folds para validación cruzada (default: 5)'
    )
    
    parser.add_argument(
        '--no-calibration',
        action='store_true',
        help='Desactivar calibración de probabilidades'
    )
    
    parser.add_argument(
        '--no-frequency',
        action='store_true',
        help='Desactivar features de frecuencia (más rápido)'
    )
    
    parser.add_argument(
        '--confidence-threshold',
        type=float,
        default=0.6,
        help='Umbral de confianza para predicciones (default: 0.6)'
    )
    
    args = parser.parse_args()
    
    # Verificar disponibilidad de optimización bayesiana
    if not BAYESIAN_AVAILABLE:
        print("="*70)
        print("ADVERTENCIA: scikit-optimize no está instalado")
        print("="*70)
        print("Para usar optimización bayesiana, instalar con:")
        print("  pip install scikit-optimize")
        print("\nContinuando sin optimización bayesiana...")
        print("="*70)
        return
    
    # Cargar datos
    print("\nCargando datos...")
    ruta_excel = settings.get_excel_path()
    
    if not ruta_excel.exists():
        print(f"ERROR: Archivo no encontrado: {ruta_excel}")
        print("   Ejecuta primero: python main.py --collect")
        return
    
    df = pd.read_excel(ruta_excel)
    
    # Validar columnas
    columnas_necesarias = {"fecha", "lottery", "result", "series"}
    if not columnas_necesarias.issubset(df.columns):
        print(f"ERROR: Faltan columnas: {columnas_necesarias - set(df.columns)}")
        return
    
    # Preprocesar
    df = df.dropna(subset=["fecha", "lottery", "result", "series"])
    df["result"] = df["result"].astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
    df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
    
    # Obtener loterías
    if args.lottery:
        loterias = [args.lottery]
    else:
        loterias = df["lottery"].str.lower().unique()
    
    use_calibration = not args.no_calibration
    use_frequency = not args.no_frequency
    
    print(f"\n{'='*70}")
    print(f"ENTRENAMIENTO MEJORADO")
    print('='*70)
    print(f"Loterías: {list(loterias)}")
    print(f"Algoritmo: {args.algorithm}")
    print(f"Iteraciones de optimización: {args.iterations}")
    print(f"CV Folds: {args.cv_folds}")
    print(f"Calibración de probabilidades: {'Activada' if use_calibration else 'Desactivada'}")
    print(f"Features de frecuencia: {'Activadas' if use_frequency else 'Desactivadas'}")
    print(f"Umbral de confianza: {args.confidence_threshold}")
    print('='*70)
    
    # Entrenar cada lotería
    for nombre_loteria in loterias:
        print(f"\n{'='*70}")
        print(f"LOTERÍA: {nombre_loteria.upper()}")
        print('='*70)
        
        df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()].copy()
        
        if len(df_loteria) < 100:
            print(f"ADVERTENCIA: Datos insuficientes: {len(df_loteria)} registros")
            print("   Se necesitan al menos 100 registros para features de frecuencia")
            continue
        
        print(f"Registros disponibles: {len(df_loteria)}")
        
        # Ordenar por fecha
        df_loteria = df_loteria.sort_values('fecha').reset_index(drop=True)
        
        # Entrenar modelo RESULT
        print(f"\n{'='*70}")
        print("MODELO: RESULT (Números)")
        print('='*70)
        
        entrenar_modelo_mejorado(
            df=df_loteria,
            lottery_name=nombre_loteria,
            model_type='result',
            target_col='result',
            algorithm=args.algorithm,
            n_iter=args.iterations,
            cv_folds=args.cv_folds,
            use_calibration=use_calibration,
            use_frequency=use_frequency,
            confidence_threshold=args.confidence_threshold
        )
        
        # Entrenar modelo SERIES
        print(f"\n{'='*70}")
        print("MODELO: SERIES (Símbolos)")
        print('='*70)
        
        entrenar_modelo_mejorado(
            df=df_loteria,
            lottery_name=nombre_loteria,
            model_type='series',
            target_col='series',
            algorithm=args.algorithm,
            n_iter=args.iterations,
            cv_folds=args.cv_folds,
            use_calibration=use_calibration,
            use_frequency=use_frequency,
            confidence_threshold=args.confidence_threshold
        )
    
    print(f"\n{'='*70}")
    print("ENTRENAMIENTO MEJORADO COMPLETADO")
    print('='*70)
    print("\nModelos guardados en: IA_models/")
    print("Logs guardados en: logs/training_enhanced.log")


def entrenar_modelo_mejorado(
    df: pd.DataFrame,
    lottery_name: str,
    model_type: str,
    target_col: str,
    algorithm: str,
    n_iter: int,
    cv_folds: int,
    use_calibration: bool,
    use_frequency: bool,
    confidence_threshold: float
):
    """
    Entrena un modelo con todas las mejoras.
    
    Args:
        df: DataFrame con datos históricos
        lottery_name: Nombre de la lotería
        model_type: 'result' o 'series'
        target_col: Columna objetivo
        algorithm: Algoritmo a usar
        n_iter: Iteraciones de optimización
        cv_folds: Folds para CV
        use_calibration: Usar calibración
        use_frequency: Usar features de frecuencia
        confidence_threshold: Umbral de confianza
    """
    # Crear features mejoradas
    print("\nGenerando features mejoradas...")
    feature_engineer = EnhancedFeatureEngineer(target_col=target_col)
    
    df_features = feature_engineer.create_all_features(
        df,
        include_frequency=use_frequency,
        include_temporal=True
    )
    
    # Seleccionar features numéricas
    feature_cols = [col for col in df_features.columns 
                   if col not in ['fecha', 'lottery', 'slug', target_col] 
                   and df_features[col].dtype in [np.int64, np.float64]]
    
    X = df_features[feature_cols].fillna(0).values
    y = df_features[target_col].values
    
    print(f"Features generadas: {len(feature_cols)}")
    print(f"Registros: {len(X)}")
    
    # Optimización bayesiana
    print(f"\nOptimizando hiperparámetros con búsqueda bayesiana...")
    optimizer = BayesianOptimizer(random_state=42)
    
    best_model, results = optimizer.optimize(
        X=X,
        y=y,
        algorithm=algorithm,
        n_iter=n_iter,
        cv=cv_folds,
        verbose=True
    )
    
    # Calibración de probabilidades
    if use_calibration:
        print(f"\nCalibrando probabilidades...")
        calibrated_wrapper = CalibratedModelWrapper(
            base_model=best_model,
            method='sigmoid',
            cv=cv_folds
        )
        calibrated_wrapper.fit(X, y)
        
        # Evaluar con umbral de confianza
        predictions, confidences, is_confident = calibrated_wrapper.predict_with_confidence(
            X,
            confidence_threshold=confidence_threshold
        )
        
        confident_pct = (is_confident.sum() / len(is_confident)) * 100
        
        print(f"\nResultados de calibración:")
        print(f"   Predicciones con confianza >= {confidence_threshold}: {confident_pct:.1f}%")
        print(f"   Confianza promedio: {confidences.mean():.4f}")
        print(f"   Confianza mínima: {confidences.min():.4f}")
        print(f"   Confianza máxima: {confidences.max():.4f}")
        
        final_model = calibrated_wrapper
    else:
        final_model = best_model
    
    # Guardar modelo
    model_filename = f"modelo_{model_type}_{lottery_name.lower().replace(' ', '_')}.pkl"
    model_path = settings.MODELS_DIR / model_filename
    
    joblib.dump(final_model, model_path)
    print(f"\nModelo guardado: {model_path}")
    
    # Guardar metadata
    metadata = {
        'lottery_name': lottery_name,
        'model_type': model_type,
        'algorithm': algorithm,
        'best_score': results['best_score'],
        'best_params': results['best_params'],
        'n_features': len(feature_cols),
        'feature_cols': feature_cols,
        'use_calibration': use_calibration,
        'use_frequency': use_frequency,
        'confidence_threshold': confidence_threshold,
        'trained_at': datetime.now().isoformat()
    }
    
    metadata_filename = f"metadata_{model_type}_{lottery_name.lower().replace(' ', '_')}.json"
    metadata_path = settings.MODELS_DIR / metadata_filename
    
    import json
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata guardada: {metadata_path}")
    
    # Log de entrenamiento
    logger.info(f"Modelo entrenado: {lottery_name} - {model_type}")
    logger.info(f"Algoritmo: {algorithm}")
    logger.info(f"Score: {results['best_score']:.4f}")
    logger.info(f"Features: {len(feature_cols)}")
    logger.info(f"Calibración: {use_calibration}")


if __name__ == "__main__":
    main()
