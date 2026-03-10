"""
Módulo de Machine Learning Avanzado con múltiples algoritmos y optimización.

Incluye:
- Validación cruzada estratificada
- Optimización de hiperparámetros (GridSearchCV, RandomizedSearchCV)
- Múltiples algoritmos (RandomForest, XGBoost, LightGBM)
- Feature engineering avanzado
- Métricas de negocio personalizadas
"""

import numpy as np
import pandas as pd
import warnings
import xgboost as xgb
import lightgbm as lgb

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import ( 
    accuracy_score, f1_score, precision_score, recall_score,
    make_scorer, classification_report
)

warnings.filterwarnings('ignore')

# Importar algoritmos avanzados si están disponibles
try:
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("!! XGBoost no disponible. Instalar con: pip install xgboost")

try:
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("!! LightGBM no disponible. Instalar con: pip install lightgbm")


class FeatureEngineer:
    """Clase para generar features avanzadas."""
    
    @staticmethod
    def add_temporal_features(df: pd.DataFrame, fecha_col: str = 'fecha') -> pd.DataFrame:
        """
        Agrega features temporales avanzadas.
        
        Args:
            df: DataFrame con columna de fecha
            fecha_col: Nombre de la columna de fecha
        
        Returns:
            DataFrame con features adicionales
        """
        df = df.copy()
        df[fecha_col] = pd.to_datetime(df[fecha_col])
        
        # Features básicas
        df['dia'] = df[fecha_col].dt.day
        df['mes'] = df[fecha_col].dt.month
        df['anio'] = df[fecha_col].dt.year
        df['dia_semana'] = df[fecha_col].dt.weekday
        df['dia_anio'] = df[fecha_col].dt.dayofyear
        df['semana_anio'] = df[fecha_col].dt.isocalendar().week
        df['trimestre'] = df[fecha_col].dt.quarter
        
        # Features cíclicas (para capturar periodicidad)
        df['dia_sin'] = np.sin(2 * np.pi * df['dia'] / 31)
        df['dia_cos'] = np.cos(2 * np.pi * df['dia'] / 31)
        df['mes_sin'] = np.sin(2 * np.pi * df['mes'] / 12)
        df['mes_cos'] = np.cos(2 * np.pi * df['mes'] / 12)
        df['dia_semana_sin'] = np.sin(2 * np.pi * df['dia_semana'] / 7)
        df['dia_semana_cos'] = np.cos(2 * np.pi * df['dia_semana'] / 7)
        
        # Fin de semana
        df['es_fin_semana'] = (df['dia_semana'] >= 5).astype(int)
        
        # Inicio/fin de mes
        df['inicio_mes'] = (df['dia'] <= 7).astype(int)
        df['fin_mes'] = (df['dia'] >= 24).astype(int)
        
        return df
    
    @staticmethod
    def add_holiday_features(df: pd.DataFrame, fecha_col: str = 'fecha') -> pd.DataFrame:
        """
        Agrega features de días festivos colombianos.
        
        Args:
            df: DataFrame con columna de fecha
            fecha_col: Nombre de la columna de fecha
        
        Returns:
            DataFrame con features de festivos
        """
        df = df.copy()
        df[fecha_col] = pd.to_datetime(df[fecha_col])
        
        # Festivos fijos principales de Colombia
        festivos_fijos = [
            (1, 1),   # Año Nuevo
            (5, 1),   # Día del Trabajo
            (7, 20),  # Día de la Independencia
            (8, 7),   # Batalla de Boyacá
            (12, 8),  # Inmaculada Concepción
            (12, 25), # Navidad
        ]
        
        df['es_festivo'] = df.apply(
            lambda row: 1 if (row[fecha_col].month, row[fecha_col].day) in festivos_fijos else 0,
            axis=1
        )
        
        # Días cercanos a festivos (±3 días)
        df['cerca_festivo'] = 0
        for idx, row in df.iterrows():
            fecha = row[fecha_col]
            for mes, dia in festivos_fijos:
                festivo = datetime(fecha.year, mes, dia)
                diff = abs((fecha - festivo).days)
                if 0 < diff <= 3:
                    df.at[idx, 'cerca_festivo'] = 1
                    break
        
        return df
    
    @staticmethod
    def add_lunar_features(df: pd.DataFrame, fecha_col: str = 'fecha') -> pd.DataFrame:
        """
        Agrega features de patrones lunares (aproximados).
        
        Args:
            df: DataFrame con columna de fecha
            fecha_col: Nombre de la columna de fecha
        
        Returns:
            DataFrame con features lunares
        """
        df = df.copy()
        df[fecha_col] = pd.to_datetime(df[fecha_col])
        
        # Ciclo lunar aproximado: 29.53 días
        # Referencia: Luna nueva el 6 de enero de 2000
        referencia = datetime(2000, 1, 6)
        
        df['dias_desde_ref'] = (df[fecha_col] - referencia).dt.days
        df['fase_lunar'] = (df['dias_desde_ref'] % 29.53) / 29.53
        
        # Features cíclicas de fase lunar
        df['fase_lunar_sin'] = np.sin(2 * np.pi * df['fase_lunar'])
        df['fase_lunar_cos'] = np.cos(2 * np.pi * df['fase_lunar'])
        
        # Clasificación de fase lunar
        df['cuarto_lunar'] = pd.cut(
            df['fase_lunar'],
            bins=[0, 0.25, 0.5, 0.75, 1.0],
            labels=[0, 1, 2, 3],
            include_lowest=True
        ).astype(int)
        
        df.drop('dias_desde_ref', axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def add_lag_features(df: pd.DataFrame, target_col: str, lags: List[int] = [1, 2, 3, 7]) -> pd.DataFrame:
        """
        Agrega features de valores históricos (lag features).
        
        Args:
            df: DataFrame ordenado por fecha
            target_col: Columna objetivo para crear lags
            lags: Lista de lags a crear
        
        Returns:
            DataFrame con lag features
        """
        df = df.copy()
        
        for lag in lags:
            df[f'{target_col}_lag_{lag}'] = df[target_col].shift(lag)
        
        return df
    
    @staticmethod
    def add_rolling_features(df: pd.DataFrame, target_col: str, windows: List[int] = [7, 14, 30]) -> pd.DataFrame:
        """
        Agrega features de ventanas móviles (rolling features).
        
        Args:
            df: DataFrame ordenado por fecha
            target_col: Columna objetivo para calcular estadísticas
            windows: Lista de tamaños de ventana
        
        Returns:
            DataFrame con rolling features
        """
        df = df.copy()
        
        for window in windows:
            df[f'{target_col}_rolling_mean_{window}'] = df[target_col].rolling(window=window, min_periods=1).mean()
            df[f'{target_col}_rolling_std_{window}'] = df[target_col].rolling(window=window, min_periods=1).std()
            df[f'{target_col}_rolling_min_{window}'] = df[target_col].rolling(window=window, min_periods=1).min()
            df[f'{target_col}_rolling_max_{window}'] = df[target_col].rolling(window=window, min_periods=1).max()
        
        return df
    
    @staticmethod
    def add_trend_features(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """
        Agrega features de tendencia.
        
        Args:
            df: DataFrame ordenado por fecha
            target_col: Columna objetivo
        
        Returns:
            DataFrame con features de tendencia
        """
        df = df.copy()
        
        # Diferencia con valor anterior
        df[f'{target_col}_diff'] = df[target_col].diff()
        
        # Tasa de cambio
        df[f'{target_col}_pct_change'] = df[target_col].pct_change()
        
        return df


class BusinessMetrics:
    """Clase para calcular métricas de negocio personalizadas."""
    
    @staticmethod
    def calculate_roi(y_true: np.ndarray, y_pred: np.ndarray, 
                     bet_amount: float = 1000, prize_multiplier: float = 5000) -> float:
        """
        Calcula el ROI (Return on Investment) simulado.
        
        Args:
            y_true: Valores reales
            y_pred: Predicciones
            bet_amount: Monto apostado por predicción
            prize_multiplier: Multiplicador del premio
        
        Returns:
            ROI como porcentaje
        """
        correct_predictions = np.sum(y_true == y_pred)
        total_predictions = len(y_true)
        
        total_invested = total_predictions * bet_amount
        total_won = correct_predictions * prize_multiplier
        
        roi = ((total_won - total_invested) / total_invested) * 100
        return roi
    
    @staticmethod
    def consecutive_hits_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Calcula la tasa de aciertos consecutivos.
        
        Args:
            y_true: Valores reales
            y_pred: Predicciones
        
        Returns:
            Tasa de aciertos consecutivos
        """
        if len(y_true) == 0:
            return 0.0
        
        consecutive = 0
        max_consecutive = 0
        
        for true, pred in zip(y_true, y_pred):
            if true == pred:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
        
        return max_consecutive / len(y_true)
    
    @staticmethod
    def prediction_confidence(model, X: np.ndarray) -> np.ndarray:
        """
        Calcula la confianza de las predicciones.
        
        Args:
            model: Modelo entrenado con predict_proba
            X: Features
        
        Returns:
            Array con confianza de cada predicción
        """
        if hasattr(model, 'predict_proba'):
            probas = model.predict_proba(X)
            confidence = np.max(probas, axis=1)
            return confidence
        else:
            return np.ones(len(X))  # Confianza 1.0 si no hay predict_proba


class AdvancedMLTrainer:
    """Clase para entrenamiento avanzado con múltiples algoritmos."""
    
    def __init__(self, cv_folds: int = 5, random_state: int = 42):
        """
        Inicializa el entrenador avanzado.
        
        Args:
            cv_folds: Número de folds para validación cruzada
            random_state: Semilla aleatoria
        """
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.best_model = None
        self.best_params = None
        self.best_score = 0.0
        self.cv_results = {}
    
    def get_algorithms(self) -> Dict[str, Any]:
        """
        Retorna diccionario de algoritmos disponibles.
        
        Returns:
            Diccionario con nombre y clase de algoritmo
        """
        algorithms = {
            'RandomForest': RandomForestClassifier(random_state=self.random_state)
        }
        
        if XGBOOST_AVAILABLE:
            algorithms['XGBoost'] = xgb.XGBClassifier(
                random_state=self.random_state,
                eval_metric='mlogloss'
            )
        
        if LIGHTGBM_AVAILABLE:
            algorithms['LightGBM'] = lgb.LGBMClassifier(
                random_state=self.random_state,
                verbose=-1
            )
        
        return algorithms
    
    def get_param_grids(self) -> Dict[str, Dict]:
        """
        Retorna grids de hiperparámetros para cada algoritmo.
        
        Returns:
            Diccionario con grids de parámetros
        """
        param_grids = {
            'RandomForest': {
                'n_estimators': [100, 200, 300],
                'max_depth': [4, 6, 8, 10],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'class_weight': ['balanced', None]
            }
        }
        
        if XGBOOST_AVAILABLE:
            param_grids['XGBoost'] = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.3],
                'subsample': [0.8, 1.0],
                'colsample_bytree': [0.8, 1.0]
            }
        
        if LIGHTGBM_AVAILABLE:
            param_grids['LightGBM'] = {
                'n_estimators': [100, 200, 300],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.3],
                'num_leaves': [31, 50, 70],
                'subsample': [0.8, 1.0]
            }
        
        return param_grids
    
    def train_with_cv(self, X: np.ndarray, y: np.ndarray, 
                     algorithm: str = 'RandomForest',
                     search_type: str = 'grid',
                     n_iter: int = 20,
                     verbose: bool = True) -> Tuple[Any, Dict]:
        """
        Entrena modelo con validación cruzada estratificada.
        
        Args:
            X: Features
            y: Target
            algorithm: Nombre del algoritmo
            search_type: 'grid' o 'random'
            n_iter: Iteraciones para RandomizedSearchCV
            verbose: Mostrar progreso
        
        Returns:
            Tupla (mejor_modelo, resultados)
        """
        algorithms = self.get_algorithms()
        param_grids = self.get_param_grids()
        
        if algorithm not in algorithms:
            raise ValueError(f"Algoritmo '{algorithm}' no disponible. Opciones: {list(algorithms.keys())}")
        
        model = algorithms[algorithm]
        param_grid = param_grids[algorithm]
        
        # Validación cruzada estratificada
        cv = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        
        # Scorer personalizado
        scoring = {
            'accuracy': 'accuracy',
            'f1_macro': 'f1_macro',
            'precision_macro': 'precision_macro',
            'recall_macro': 'recall_macro'
        }
        
        if verbose:
            print(f"\n>> Entrenando {algorithm} con {search_type.upper()} Search...")
            print(f"   CV Folds: {self.cv_folds}")
            print(f"   Param Grid: {len(param_grid)} parámetros")
        
        # Búsqueda de hiperparámetros
        if search_type == 'grid':
            search = GridSearchCV(
                model,
                param_grid,
                cv=cv,
                scoring=scoring,
                refit='accuracy',
                n_jobs=-1,
                verbose=1 if verbose else 0
            )
        else:  # random
            search = RandomizedSearchCV(
                model,
                param_grid,
                n_iter=n_iter,
                cv=cv,
                scoring=scoring,
                refit='accuracy',
                n_jobs=-1,
                random_state=self.random_state,
                verbose=1 if verbose else 0
            )
        
        search.fit(X, y)
        
        results = {
            'best_score': search.best_score_,
            'best_params': search.best_params_,
            'cv_results': search.cv_results_,
            'best_estimator': search.best_estimator_
        }
        
        if verbose:
            print(f"\n   Mejor Score (CV): {search.best_score_:.4f}")
            print(f"   Mejores Parámetros:")
            for param, value in search.best_params_.items():
                print(f"      {param}: {value}")
        
        self.best_model = search.best_estimator_
        self.best_params = search.best_params_
        self.best_score = search.best_score_
        self.cv_results = results
        
        return search.best_estimator_, results
    
    def compare_algorithms(self, X: np.ndarray, y: np.ndarray, 
                          search_type: str = 'random',
                          n_iter: int = 10,
                          verbose: bool = True) -> Dict[str, Dict]:
        """
        Compara múltiples algoritmos y retorna el mejor.
        
        Args:
            X: Features
            y: Target
            search_type: 'grid' o 'random'
            n_iter: Iteraciones para RandomizedSearchCV
            verbose: Mostrar progreso
        
        Returns:
            Diccionario con resultados de cada algoritmo
        """
        algorithms = self.get_algorithms()
        results = {}
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"COMPARACIÓN DE ALGORITMOS")
            print(f"{'='*60}")
            print(f"Algoritmos disponibles: {list(algorithms.keys())}")
            print(f"Método de búsqueda: {search_type.upper()}")
        
        for algo_name in algorithms.keys():
            try:
                model, result = self.train_with_cv(
                    X, y,
                    algorithm=algo_name,
                    search_type=search_type,
                    n_iter=n_iter,
                    verbose=verbose
                )
                results[algo_name] = result
            except Exception as e:
                if verbose:
                    print(f"\n!! Error entrenando {algo_name}: {e}")
                results[algo_name] = {'error': str(e)}
        
        # Encontrar el mejor algoritmo
        best_algo = max(
            [(name, res.get('best_score', 0)) for name, res in results.items() if 'error' not in res],
            key=lambda x: x[1]
        )
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"RESUMEN DE COMPARACIÓN")
            print(f"{'='*60}")
            for algo_name, result in results.items():
                if 'error' in result:
                    print(f"   {algo_name}: ERROR - {result['error']}")
                else:
                    score = result.get('best_score', 0)
                    marker = "🏆" if algo_name == best_algo[0] else "  "
                    print(f"   {marker} {algo_name}: {score:.4f}")
            print(f"\n>> Mejor algoritmo: {best_algo[0]} (Score: {best_algo[1]:.4f})")
        
        self.best_model = results[best_algo[0]]['best_estimator']
        self.best_score = best_algo[1]
        
        return results
    
    def evaluate_with_business_metrics(self, X_test: np.ndarray, y_test: np.ndarray,
                                      verbose: bool = True) -> Dict[str, float]:
        """
        Evalúa el modelo con métricas de negocio.
        
        Args:
            X_test: Features de prueba
            y_test: Target de prueba
            verbose: Mostrar resultados
        
        Returns:
            Diccionario con métricas
        """
        if self.best_model is None:
            raise ValueError("Debe entrenar un modelo primero")
        
        y_pred = self.best_model.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'f1_macro': f1_score(y_test, y_pred, average='macro'),
            'precision_macro': precision_score(y_test, y_pred, average='macro', zero_division=0),
            'recall_macro': recall_score(y_test, y_pred, average='macro', zero_division=0),
            'roi': BusinessMetrics.calculate_roi(y_test, y_pred),
            'consecutive_hits_rate': BusinessMetrics.consecutive_hits_rate(y_test, y_pred),
            'avg_confidence': np.mean(BusinessMetrics.prediction_confidence(self.best_model, X_test))
        }
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"MÉTRICAS DE EVALUACIÓN")
            print(f"{'='*60}")
            print(f"   Accuracy: {metrics['accuracy']:.4f}")
            print(f"   F1-Score (Macro): {metrics['f1_macro']:.4f}")
            print(f"   Precision (Macro): {metrics['precision_macro']:.4f}")
            print(f"   Recall (Macro): {metrics['recall_macro']:.4f}")
            print(f"\n   MÉTRICAS DE NEGOCIO:")
            print(f"   ROI Simulado: {metrics['roi']:.2f}%")
            print(f"   Tasa Aciertos Consecutivos: {metrics['consecutive_hits_rate']:.4f}")
            print(f"   Confianza Promedio: {metrics['avg_confidence']:.4f}")
        
        return metrics
