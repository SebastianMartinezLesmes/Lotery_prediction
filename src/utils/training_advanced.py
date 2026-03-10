"""
Sistema de entrenamiento avanzado con ML mejorado.

Integra:
- Validación cruzada estratificada
- Optimización de hiperparámetros
- Múltiples algoritmos
- Feature engineering avanzado
- Métricas de negocio
"""

import os
import sys
import joblib
import traceback
import numpy as np
import pandas as pd

from pathlib import Path
from src.core.config import settings
from sklearn.model_selection import train_test_split
from src.utils.training_visualizer import TrainingVisualizer
from src.utils.ml_advanced import (
    FeatureEngineer,
    AdvancedMLTrainer,
    BusinessMetrics
)
from typing import (
    Tuple,
    Dict,
    Any,
    Optional
)


def preparar_datos_avanzados(df: pd.DataFrame, enable_feature_engineering: bool = True) -> Tuple[pd.DataFrame, list]:
    """
    Prepara datos con feature engineering avanzado.
    
    Args:
        df: DataFrame con datos crudos
        enable_feature_engineering: Habilitar feature engineering
    
    Returns:
        Tupla (DataFrame procesado, lista de columnas de features)
    """
    df = df.copy()
    
    # Asegurar que fecha es datetime
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True)
    
    # Ordenar por fecha
    df = df.sort_values('fecha').reset_index(drop=True)
    
    # Features básicas
    feature_cols = []
    
    if enable_feature_engineering:
        print("   >> Generando features avanzadas...")
        
        # Features temporales
        df = FeatureEngineer.add_temporal_features(df, 'fecha')
        feature_cols.extend([
            'dia', 'mes', 'anio', 'dia_semana', 'dia_anio', 'semana_anio', 'trimestre',
            'dia_sin', 'dia_cos', 'mes_sin', 'mes_cos', 'dia_semana_sin', 'dia_semana_cos',
            'es_fin_semana', 'inicio_mes', 'fin_mes'
        ])
        
        # Features de festivos
        df = FeatureEngineer.add_holiday_features(df, 'fecha')
        feature_cols.extend(['es_festivo', 'cerca_festivo'])
        
        # Features lunares
        df = FeatureEngineer.add_lunar_features(df, 'fecha')
        feature_cols.extend(['fase_lunar', 'fase_lunar_sin', 'fase_lunar_cos', 'cuarto_lunar'])
        
        # Features de lag (valores históricos)
        if 'result' in df.columns:
            df = FeatureEngineer.add_lag_features(df, 'result', lags=[1, 2, 3, 7])
            feature_cols.extend(['result_lag_1', 'result_lag_2', 'result_lag_3', 'result_lag_7'])
        
        # Features de rolling (ventanas móviles)
        if 'result' in df.columns:
            df = FeatureEngineer.add_rolling_features(df, 'result', windows=[7, 14])
            feature_cols.extend([
                'result_rolling_mean_7', 'result_rolling_std_7',
                'result_rolling_min_7', 'result_rolling_max_7',
                'result_rolling_mean_14', 'result_rolling_std_14',
                'result_rolling_min_14', 'result_rolling_max_14'
            ])
        
        # Features de tendencia
        if 'result' in df.columns:
            df = FeatureEngineer.add_trend_features(df, 'result')
            feature_cols.extend(['result_diff', 'result_pct_change'])
        
        print(f"   >> Features generadas: {len(feature_cols)}")
    else:
        # Solo features básicas
        df = FeatureEngineer.add_temporal_features(df, 'fecha')
        feature_cols = ['dia', 'mes', 'anio', 'dia_semana']
        print(f"   >> Usando features básicas: {len(feature_cols)}")
    
    # Eliminar filas con NaN (generadas por lag/rolling)
    df = df.dropna()
    
    return df, feature_cols


def entrenar_modelo_avanzado(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    lottery_name: str,
    algorithm: str = 'RandomForest',
    search_type: str = 'random',
    search_iterations: int = 20,
    cv_folds: int = 5,
    verbose: bool = True
) -> Tuple[Any, Dict]:
    """
    Entrena un modelo con configuración avanzada.
    
    Args:
        X: Features
        y: Target
        model_type: 'result' o 'series'
        lottery_name: Nombre de la lotería
        algorithm: Algoritmo a usar
        search_type: Tipo de búsqueda de hiperparámetros
        search_iterations: Iteraciones para búsqueda
        cv_folds: Folds para validación cruzada
        verbose: Mostrar progreso
    
    Returns:
        Tupla (modelo entrenado, métricas)
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"ENTRENAMIENTO AVANZADO - {model_type.upper()}")
        print(f"{'='*60}")
        print(f"   Lotería: {lottery_name}")
        print(f"   Algoritmo: {algorithm}")
        print(f"   Búsqueda: {search_type}")
        print(f"   CV Folds: {cv_folds}")
        print(f"   Samples: {len(X)}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Clases únicas: {len(np.unique(y))}")
    
    # Inicializar entrenador
    trainer = AdvancedMLTrainer(cv_folds=cv_folds, random_state=42)
    
    # Entrenar según configuración
    if algorithm.lower() == 'auto':
        # Comparar todos los algoritmos disponibles
        results = trainer.compare_algorithms(
            X, y,
            search_type=search_type,
            n_iter=search_iterations,
            verbose=verbose
        )
        best_model = trainer.best_model
        best_score = trainer.best_score
    else:
        # Entrenar algoritmo específico
        best_model, results = trainer.train_with_cv(
            X, y,
            algorithm=algorithm,
            search_type=search_type,
            n_iter=search_iterations,
            verbose=verbose
        )
        best_score = results['best_score']
    
    metrics = {
        'cv_score': best_score,
        'best_params': trainer.best_params,
        'algorithm': algorithm
    }
    
    return best_model, metrics


def entrenar_loteria_avanzado(
    df: pd.DataFrame,
    lottery_name: str,
    enable_feature_engineering: bool = True,
    algorithm: str = 'RandomForest',
    search_type: str = 'random',
    search_iterations: int = 20,
    cv_folds: int = 5,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Entrena modelos para una lotería con configuración avanzada.
    
    Args:
        df: DataFrame con datos de la lotería
        lottery_name: Nombre de la lotería
        enable_feature_engineering: Habilitar feature engineering
        algorithm: Algoritmo a usar
        search_type: Tipo de búsqueda
        search_iterations: Iteraciones de búsqueda
        cv_folds: Folds para CV
        verbose: Mostrar progreso
    
    Returns:
        Diccionario con modelos y métricas
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"ENTRENAMIENTO AVANZADO: {lottery_name.upper()}")
        print(f"{'='*70}")
    
    # Preparar datos
    df_processed, feature_cols = preparar_datos_avanzados(df, enable_feature_engineering)
    
    # Extraer features y targets
    X = df_processed[feature_cols].values
    y_result = df_processed['result'].values
    
    # Convertir series a códigos numéricos si es necesario
    if df_processed['series'].dtype == 'object':
        df_processed['series'] = df_processed['series'].astype('category').cat.codes
    y_series = df_processed['series'].values
    
    # Entrenar modelo de resultados
    if verbose:
        print(f"\n>> Entrenando modelo RESULT...")
    
    model_result, metrics_result = entrenar_modelo_avanzado(
        X, y_result,
        model_type='result',
        lottery_name=lottery_name,
        algorithm=algorithm,
        search_type=search_type,
        search_iterations=search_iterations,
        cv_folds=cv_folds,
        verbose=verbose
    )
    
    # Entrenar modelo de series
    if verbose:
        print(f"\n>> Entrenando modelo SERIES...")
    
    model_series, metrics_series = entrenar_modelo_avanzado(
        X, y_series,
        model_type='series',
        lottery_name=lottery_name,
        algorithm=algorithm,
        search_type=search_type,
        search_iterations=search_iterations,
        cv_folds=cv_folds,
        verbose=verbose
    )
    
    # Evaluar con métricas de negocio
    if verbose:
        print(f"\n{'='*60}")
        print(f"EVALUACIÓN CON MÉTRICAS DE NEGOCIO")
        print(f"{'='*60}")
    
    # Split para evaluación final
    X_train, X_test, y_result_train, y_result_test = train_test_split(
        X, y_result, test_size=0.2, random_state=42
    )
    _, _, y_series_train, y_series_test = train_test_split(
        X, y_series, test_size=0.2, random_state=42
    )
    
    # Evaluar modelo result
    trainer_result = AdvancedMLTrainer()
    trainer_result.best_model = model_result
    business_metrics_result = trainer_result.evaluate_with_business_metrics(
        X_test, y_result_test, verbose=verbose
    )
    
    # Evaluar modelo series
    if verbose:
        print(f"\n{'='*60}")
        print(f"MÉTRICAS MODELO SERIES")
        print(f"{'='*60}")
    
    trainer_series = AdvancedMLTrainer()
    trainer_series.best_model = model_series
    business_metrics_series = trainer_series.evaluate_with_business_metrics(
        X_test, y_series_test, verbose=verbose
    )
    
    # Guardar modelos
    model_result_path = settings.get_model_path(lottery_name, 'result')
    model_series_path = settings.get_model_path(lottery_name, 'series')
    
    joblib.dump(model_result, model_result_path)
    joblib.dump(model_series, model_series_path)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"MODELOS GUARDADOS")
        print(f"{'='*60}")
        print(f"   Result: {model_result_path}")
        print(f"   Series: {model_series_path}")
    
    return {
        'model_result': model_result,
        'model_series': model_series,
        'metrics_result': {**metrics_result, **business_metrics_result},
        'metrics_series': {**metrics_series, **business_metrics_series},
        'feature_cols': feature_cols
    }


def main():
    """Función principal para entrenamiento avanzado."""
    print("="*70)
    print("SISTEMA DE ENTRENAMIENTO AVANZADO DE ML")
    print("="*70)
    
    # Cargar configuración
    use_advanced = settings.USE_ADVANCED_ML
    algorithm = settings.ML_ALGORITHM
    search_type = settings.HYPERPARAMETER_SEARCH
    search_iterations = settings.SEARCH_ITERATIONS
    cv_folds = settings.CV_FOLDS
    enable_fe = settings.ENABLE_FEATURE_ENGINEERING
    
    print(f"\nConfiguración:")
    print(f"   Modo Avanzado: {use_advanced}")
    print(f"   Algoritmo: {algorithm}")
    print(f"   Búsqueda: {search_type}")
    print(f"   Iteraciones: {search_iterations}")
    print(f"   CV Folds: {cv_folds}")
    print(f"   Feature Engineering: {enable_fe}")
    
    # Cargar datos
    excel_path = settings.get_excel_path()
    
    if not excel_path.exists():
        print(f"\n!! Error: Archivo no encontrado: {excel_path}")
        print(f"   Ejecutar primero: python main.py --collect")
        sys.exit(1)
    
    print(f"\n>> Cargando datos desde: {excel_path}")
    df = pd.read_excel(excel_path)
    
    # Validar columnas
    required_cols = {'fecha', 'lottery', 'result', 'series'}
    if not required_cols.issubset(df.columns):
        print(f"\n!! Error: Faltan columnas requeridas: {required_cols - set(df.columns)}")
        sys.exit(1)
    
    # Limpiar datos
    df = df.dropna(subset=['fecha', 'lottery', 'result', 'series'])
    df['result'] = df['result'].astype(int)
    
    # Obtener loterías únicas
    lotteries = df['lottery'].str.lower().unique()
    print(f"\n>> Loterías encontradas: {list(lotteries)}")
    
    # Entrenar cada lotería
    all_results = {}
    
    for lottery in lotteries:
        df_lottery = df[df['lottery'].str.lower() == lottery].copy()
        
        if len(df_lottery) < 50:
            print(f"\n!! Advertencia: {lottery} tiene solo {len(df_lottery)} registros. Saltando...")
            continue
        
        try:
            results = entrenar_loteria_avanzado(
                df_lottery,
                lottery_name=lottery,
                enable_feature_engineering=enable_fe,
                algorithm=algorithm,
                search_type=search_type,
                search_iterations=search_iterations,
                cv_folds=cv_folds,
                verbose=True
            )
            all_results[lottery] = results
        except Exception as e:
            print(f"\n!! Error entrenando {lottery}: {e}")
            traceback.print_exc()
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"RESUMEN FINAL")
    print(f"{'='*70}")
    
    for lottery, results in all_results.items():
        print(f"\n{lottery.upper()}:")
        print(f"   Result - CV Score: {results['metrics_result']['cv_score']:.4f}")
        print(f"   Result - Accuracy: {results['metrics_result']['accuracy']:.4f}")
        print(f"   Result - ROI: {results['metrics_result']['roi']:.2f}%")
        print(f"   Series - CV Score: {results['metrics_series']['cv_score']:.4f}")
        print(f"   Series - Accuracy: {results['metrics_series']['accuracy']:.4f}")
        print(f"   Series - ROI: {results['metrics_series']['roi']:.2f}%")
    
    print(f"\n{'='*70}")
    print(f"ENTRENAMIENTO COMPLETADO")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
