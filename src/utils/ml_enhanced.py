"""
Módulo de Machine Learning Mejorado con features avanzadas.

Mejoras implementadas:
1. Features de frecuencia y patrones (números calientes/fríos)
2. Calibración de probabilidades
3. Optimización bayesiana de hiperparámetros

Autor: Sistema de Predicción de Lotería
Fecha: Febrero 2026
"""

import warnings
import numpy as np
import pandas as pd
import xgboost as xgb
import lightgbm as lgb

from datetime import datetime
from collections import Counter
from typing import Dict, List, Tuple, Optional, Any

from skopt import BayesSearchCV
from skopt.space import Real, Integer, Categorical
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.calibration import CalibratedClassifierCV


warnings.filterwarnings('ignore')

# Importar algoritmos avanzados
try:
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# Importar optimización bayesiana
try:
    BAYESIAN_AVAILABLE = True
except ImportError:
    BAYESIAN_AVAILABLE = False
    print("!! scikit-optimize no disponible. Instalar con: pip install scikit-optimize")


class FrequencyPatternEngineer:
    """
    Clase para generar features basadas en frecuencia y patrones históricos.
    
    Features generadas:
    - Frecuencia de aparición de cada valor
    - Números calientes (más frecuentes últimamente)
    - Números fríos (menos frecuentes últimamente)
    - Intervalos entre apariciones
    - Tendencias de frecuencia
    """
    
    def __init__(self, target_col: str = 'result'):
        """
        Inicializa el generador de features de frecuencia.
        
        Args:
            target_col: Columna objetivo para analizar patrones
        """
        self.target_col = target_col
        self.frequency_cache = {}
        self.interval_cache = {}
    
    def add_frequency_features(
        self,
        df: pd.DataFrame,
        windows: List[int] = [7, 14, 30, 60, 90]
    ) -> pd.DataFrame:
        """
        Agrega features de frecuencia de aparición.
        
        Args:
            df: DataFrame ordenado por fecha con columna target
            windows: Ventanas de tiempo para calcular frecuencias
        
        Returns:
            DataFrame con features de frecuencia
        """
        df = df.copy()
        
        if self.target_col not in df.columns:
            return df
        
        # Frecuencia global (histórica completa)
        value_counts = df[self.target_col].value_counts()
        df[f'{self.target_col}_freq_global'] = df[self.target_col].map(value_counts)
        df[f'{self.target_col}_freq_global_norm'] = df[f'{self.target_col}_freq_global'] / len(df)
        
        # Frecuencias en ventanas móviles
        for window in windows:
            freq_col = f'{self.target_col}_freq_{window}d'
            df[freq_col] = 0
            
            for idx in range(len(df)):
                if idx < window:
                    # No hay suficiente historia
                    df.at[idx, freq_col] = 0
                else:
                    # Contar apariciones en la ventana
                    window_data = df.iloc[idx-window:idx][self.target_col]
                    current_value = df.iloc[idx][self.target_col]
                    df.at[idx, freq_col] = (window_data == current_value).sum()
        
        return df
    
    def add_hot_cold_features(
        self,
        df: pd.DataFrame,
        hot_window: int = 30,
        cold_window: int = 90,
        top_n: int = 10
    ) -> pd.DataFrame:
        """
        Agrega features de números calientes y fríos.
        
        Args:
            df: DataFrame ordenado por fecha
            hot_window: Ventana para números calientes (días recientes)
            cold_window: Ventana para números fríos (días históricos)
            top_n: Número de valores top a considerar
        
        Returns:
            DataFrame con features hot/cold
        """
        df = df.copy()
        
        if self.target_col not in df.columns:
            return df
        
        df[f'{self.target_col}_is_hot'] = 0
        df[f'{self.target_col}_is_cold'] = 0
        df[f'{self.target_col}_hot_rank'] = 0
        df[f'{self.target_col}_cold_rank'] = 0
        
        for idx in range(len(df)):
            # Números calientes (últimos N días)
            if idx >= hot_window:
                hot_data = df.iloc[idx-hot_window:idx][self.target_col]
                hot_counts = Counter(hot_data)
                hot_numbers = [num for num, _ in hot_counts.most_common(top_n)]
                
                current_value = df.iloc[idx][self.target_col]
                if current_value in hot_numbers:
                    df.at[idx, f'{self.target_col}_is_hot'] = 1
                    df.at[idx, f'{self.target_col}_hot_rank'] = hot_numbers.index(current_value) + 1
            
            # Números fríos (histórico completo hasta cold_window atrás)
            if idx >= cold_window:
                cold_data = df.iloc[idx-cold_window:idx][self.target_col]
                cold_counts = Counter(cold_data)
                # Los menos comunes son los "fríos"
                cold_numbers = [num for num, _ in cold_counts.most_common()[-top_n:]]
                
                current_value = df.iloc[idx][self.target_col]
                if current_value in cold_numbers:
                    df.at[idx, f'{self.target_col}_is_cold'] = 1
                    df.at[idx, f'{self.target_col}_cold_rank'] = cold_numbers.index(current_value) + 1
        
        return df
    
    def add_interval_features(
        self,
        df: pd.DataFrame,
        max_lookback: int = 100
    ) -> pd.DataFrame:
        """
        Agrega features de intervalos entre apariciones.
        
        Args:
            df: DataFrame ordenado por fecha
            max_lookback: Máximo de registros hacia atrás para buscar
        
        Returns:
            DataFrame con features de intervalos
        """
        df = df.copy()
        
        if self.target_col not in df.columns:
            return df
        
        df[f'{self.target_col}_days_since_last'] = 0
        df[f'{self.target_col}_avg_interval'] = 0
        df[f'{self.target_col}_min_interval'] = 0
        df[f'{self.target_col}_max_interval'] = 0
        
        for idx in range(len(df)):
            current_value = df.iloc[idx][self.target_col]
            
            # Buscar apariciones previas del mismo valor
            lookback_start = max(0, idx - max_lookback)
            previous_data = df.iloc[lookback_start:idx]
            
            # Encontrar índices donde apareció el mismo valor
            same_value_indices = previous_data[previous_data[self.target_col] == current_value].index.tolist()
            
            if same_value_indices:
                # Días desde última aparición
                last_idx = same_value_indices[-1]
                days_since = idx - last_idx
                df.at[idx, f'{self.target_col}_days_since_last'] = days_since
                
                # Calcular intervalos entre apariciones
                if len(same_value_indices) > 1:
                    intervals = []
                    for i in range(1, len(same_value_indices)):
                        interval = same_value_indices[i] - same_value_indices[i-1]
                        intervals.append(interval)
                    
                    df.at[idx, f'{self.target_col}_avg_interval'] = np.mean(intervals)
                    df.at[idx, f'{self.target_col}_min_interval'] = np.min(intervals)
                    df.at[idx, f'{self.target_col}_max_interval'] = np.max(intervals)
            else:
                # Primera aparición o no encontrada en lookback
                df.at[idx, f'{self.target_col}_days_since_last'] = max_lookback
        
        return df
    
    def add_trend_features(
        self,
        df: pd.DataFrame,
        windows: List[int] = [7, 14, 30]
    ) -> pd.DataFrame:
        """
        Agrega features de tendencia de frecuencia.
        
        Args:
            df: DataFrame ordenado por fecha
            windows: Ventanas para calcular tendencias
        
        Returns:
            DataFrame con features de tendencia
        """
        df = df.copy()
        
        if self.target_col not in df.columns:
            return df
        
        for window in windows:
            trend_col = f'{self.target_col}_freq_trend_{window}d'
            df[trend_col] = 0
            
            for idx in range(len(df)):
                if idx < window * 2:
                    continue
                
                current_value = df.iloc[idx][self.target_col]
                
                # Frecuencia en ventana reciente
                recent_data = df.iloc[idx-window:idx][self.target_col]
                recent_freq = (recent_data == current_value).sum()
                
                # Frecuencia en ventana anterior
                old_data = df.iloc[idx-window*2:idx-window][self.target_col]
                old_freq = (old_data == current_value).sum()
                
                # Tendencia: positiva si aumenta, negativa si disminuye
                if old_freq > 0:
                    trend = (recent_freq - old_freq) / old_freq
                else:
                    trend = 1.0 if recent_freq > 0 else 0.0
                
                df.at[idx, trend_col] = trend
        
        return df
    
    def create_all_frequency_features(
        self,
        df: pd.DataFrame,
        freq_windows: List[int] = [7, 14, 30, 60, 90],
        hot_window: int = 30,
        cold_window: int = 90,
        trend_windows: List[int] = [7, 14, 30]
    ) -> pd.DataFrame:
        """
        Crea todas las features de frecuencia y patrones.
        
        Args:
            df: DataFrame ordenado por fecha
            freq_windows: Ventanas para frecuencias
            hot_window: Ventana para números calientes
            cold_window: Ventana para números fríos
            trend_windows: Ventanas para tendencias
        
        Returns:
            DataFrame con todas las features
        """
        df = self.add_frequency_features(df, windows=freq_windows)
        df = self.add_hot_cold_features(df, hot_window=hot_window, cold_window=cold_window)
        df = self.add_interval_features(df)
        df = self.add_trend_features(df, windows=trend_windows)
        
        return df


class CalibratedModelWrapper:
    """
    Wrapper para modelos con calibración de probabilidades.
    
    La calibración mejora la confiabilidad de las probabilidades predichas,
    lo que permite tomar mejores decisiones sobre cuándo confiar en una predicción.
    """
    
    def __init__(self, base_model, method: str = 'sigmoid', cv: int = 5):
        """
        Inicializa el wrapper con calibración.
        
        Args:
            base_model: Modelo base a calibrar
            method: Método de calibración ('sigmoid' o 'isotonic')
            cv: Número de folds para calibración
        """
        self.base_model = base_model
        self.method = method
        self.cv = cv
        self.calibrated_model = None
    
    def fit(self, X, y):
        """Entrena y calibra el modelo."""
        # Entrenar modelo base
        self.base_model.fit(X, y)
        
        # Calibrar probabilidades
        self.calibrated_model = CalibratedClassifierCV(
            self.base_model,
            method=self.method,
            cv=self.cv
        )
        self.calibrated_model.fit(X, y)
        
        return self
    
    def predict(self, X):
        """Predice clases."""
        if self.calibrated_model is None:
            raise ValueError("Modelo no entrenado. Llamar fit() primero.")
        return self.calibrated_model.predict(X)
    
    def predict_proba(self, X):
        """Predice probabilidades calibradas."""
        if self.calibrated_model is None:
            raise ValueError("Modelo no entrenado. Llamar fit() primero.")
        return self.calibrated_model.predict_proba(X)
    
    def predict_with_confidence(self, X, confidence_threshold: float = 0.6):
        """
        Predice con umbral de confianza.
        
        Args:
            X: Features
            confidence_threshold: Umbral mínimo de confianza (0-1)
        
        Returns:
            Tupla (predicciones, confianzas, es_confiable)
        """
        probas = self.predict_proba(X)
        predictions = self.predict(X)
        confidences = np.max(probas, axis=1)
        is_confident = confidences >= confidence_threshold
        
        return predictions, confidences, is_confident


class BayesianOptimizer:
    """
    Optimizador bayesiano de hiperparámetros.
    
    Más eficiente que GridSearch o RandomSearch, encuentra mejores
    hiperparámetros en menos iteraciones.
    """
    
    def __init__(self, random_state: int = 42):
        """
        Inicializa el optimizador bayesiano.
        
        Args:
            random_state: Semilla aleatoria
        """
        self.random_state = random_state
        self.best_model = None
        self.best_params = None
        self.best_score = 0.0
    
    def get_search_spaces(self) -> Dict[str, Dict]:
        """
        Retorna espacios de búsqueda para optimización bayesiana.
        
        Returns:
            Diccionario con espacios de búsqueda por algoritmo
        """
        search_spaces = {
            'RandomForest': {
                'n_estimators': Integer(50, 500),
                'max_depth': Integer(3, 15),
                'min_samples_split': Integer(2, 20),
                'min_samples_leaf': Integer(1, 10),
                'max_features': Categorical(['sqrt', 'log2', None]),
                'class_weight': Categorical(['balanced', None])
            }
        }
        
        if XGBOOST_AVAILABLE:
            search_spaces['XGBoost'] = {
                'n_estimators': Integer(50, 500),
                'max_depth': Integer(3, 12),
                'learning_rate': Real(0.001, 0.3, prior='log-uniform'),
                'subsample': Real(0.6, 1.0),
                'colsample_bytree': Real(0.6, 1.0),
                'min_child_weight': Integer(1, 10),
                'gamma': Real(0, 5)
            }
        
        if LIGHTGBM_AVAILABLE:
            search_spaces['LightGBM'] = {
                'n_estimators': Integer(50, 500),
                'max_depth': Integer(3, 12),
                'learning_rate': Real(0.001, 0.3, prior='log-uniform'),
                'num_leaves': Integer(20, 150),
                'subsample': Real(0.6, 1.0),
                'colsample_bytree': Real(0.6, 1.0),
                'min_child_samples': Integer(5, 100)
            }
        
        return search_spaces
    
    def optimize(
        self,
        X,
        y,
        algorithm: str = 'RandomForest',
        n_iter: int = 50,
        cv: int = 5,
        verbose: bool = True
    ) -> Tuple[Any, Dict]:
        """
        Optimiza hiperparámetros usando búsqueda bayesiana.
        
        Args:
            X: Features
            y: Target
            algorithm: Nombre del algoritmo
            n_iter: Número de iteraciones
            cv: Folds para validación cruzada
            verbose: Mostrar progreso
        
        Returns:
            Tupla (mejor_modelo, resultados)
        """
        if not BAYESIAN_AVAILABLE:
            raise ImportError("scikit-optimize no disponible. Instalar con: pip install scikit-optimize")
        
        # Obtener modelo base
        if algorithm == 'RandomForest':
            base_model = RandomForestClassifier(random_state=self.random_state, n_jobs=-1)
        elif algorithm == 'XGBoost' and XGBOOST_AVAILABLE:
            base_model = xgb.XGBClassifier(random_state=self.random_state, n_jobs=-1, eval_metric='mlogloss')
        elif algorithm == 'LightGBM' and LIGHTGBM_AVAILABLE:
            base_model = lgb.LGBMClassifier(random_state=self.random_state, n_jobs=-1, verbose=-1)
        else:
            raise ValueError(f"Algoritmo '{algorithm}' no disponible")
        
        # Obtener espacio de búsqueda
        search_spaces = self.get_search_spaces()
        search_space = search_spaces[algorithm]
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"OPTIMIZACIÓN BAYESIANA - {algorithm}")
            print('='*70)
            print(f"Iteraciones: {n_iter}")
            print(f"CV Folds: {cv}")
            print(f"Espacio de búsqueda: {len(search_space)} parámetros")
        
        # Búsqueda bayesiana
        bayes_search = BayesSearchCV(
            base_model,
            search_space,
            n_iter=n_iter,
            cv=cv,
            n_jobs=-1,
            random_state=self.random_state,
            verbose=1 if verbose else 0,
            scoring='accuracy'
        )
        
        bayes_search.fit(X, y)
        
        self.best_model = bayes_search.best_estimator_
        self.best_params = bayes_search.best_params_
        self.best_score = bayes_search.best_score_
        
        results = {
            'best_score': bayes_search.best_score_,
            'best_params': bayes_search.best_params_,
            'cv_results': bayes_search.cv_results_,
            'best_estimator': bayes_search.best_estimator_
        }
        
        if verbose:
            print(f"\n{'='*70}")
            print("RESULTADOS DE OPTIMIZACIÓN")
            print('='*70)
            print(f"Mejor Score (CV): {bayes_search.best_score_:.4f}")
            print(f"\nMejores Hiperparámetros:")
            for param, value in bayes_search.best_params_.items():
                print(f"   {param}: {value}")
            print('='*70)
        
        return bayes_search.best_estimator_, results


# Clase de conveniencia para usar todas las mejoras juntas
class EnhancedFeatureEngineer:
    """
    Clase que combina todas las mejoras de feature engineering.
    """
    
    def __init__(self, target_col: str = 'result'):
        """
        Inicializa el ingeniero de features mejorado.
        
        Args:
            target_col: Columna objetivo
        """
        self.target_col = target_col
        self.freq_engineer = FrequencyPatternEngineer(target_col=target_col)
    
    def create_all_features(
        self,
        df: pd.DataFrame,
        include_frequency: bool = True,
        include_temporal: bool = True
    ) -> pd.DataFrame:
        """
        Crea todas las features mejoradas.
        
        Args:
            df: DataFrame con datos históricos
            include_frequency: Incluir features de frecuencia
            include_temporal: Incluir features temporales básicas
        
        Returns:
            DataFrame con todas las features
        """
        df = df.copy()
        
        # Features temporales básicas
        if include_temporal and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['dia'] = df['fecha'].dt.day
            df['mes'] = df['fecha'].dt.month
            df['anio'] = df['fecha'].dt.year
            df['dia_semana'] = df['fecha'].dt.weekday
        
        # Features de frecuencia y patrones
        if include_frequency:
            df = self.freq_engineer.create_all_frequency_features(df)
        
        return df


if __name__ == "__main__":
    print("Módulo de ML Mejorado")
    print("Incluye:")
    print("  1. Features de frecuencia y patrones")
    print("  2. Calibración de probabilidades")
    print("  3. Optimización bayesiana")
    print(f"\nOptimización bayesiana disponible: {BAYESIAN_AVAILABLE}")
