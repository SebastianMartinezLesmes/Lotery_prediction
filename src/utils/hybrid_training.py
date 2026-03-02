"""
Sistema de Entrenamiento Híbrido Mejorado.
Combina entrenamiento evolutivo con múltiples algoritmos y TODAS las mejoras de ML.

Mejoras integradas:
1. Features de frecuencia y patrones (números calientes/fríos)
2. Calibración de probabilidades (confianza real)
3. Optimización bayesiana (mejores hiperparámetros)

Variantes:
1. RandomForest (rápido, robusto)
2. XGBoost (preciso, potente)
3. LightGBM (eficiente, rápido)

Cada variante compite y evoluciona con todas las mejoras.
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import json
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

from src.core.config import settings
from src.core.logger import LoggerManager
from src.utils.ml_advanced import FeatureEngineer
from src.utils.ml_enhanced import (
    EnhancedFeatureEngineer,
    CalibratedModelWrapper,
    BayesianOptimizer,
    BAYESIAN_AVAILABLE
)

# Importar algoritmos avanzados
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

logger = LoggerManager.get_logger("hybrid_training", "hybrid.log")


@dataclass
class HybridVariant:
    """Representa una variante híbrida con algoritmo específico."""
    id: int
    role: str  # "PRODUCTION", "EXPERIMENTAL_1", "EXPERIMENTAL_2"
    algorithm: str  # "RandomForest", "XGBoost", "LightGBM"
    accuracy: float
    f1_score: float
    hyperparameters: Dict
    iterations_trained: int
    last_improvement: int
    created_at: str
    is_calibrated: bool = False  # Nueva: indica si está calibrado
    confidence_threshold: float = 0.6  # Nueva: umbral de confianza
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HybridVariant':
        return cls(**data)


class HybridTrainer:
    """
    Entrenador híbrido mejorado que combina:
    - Múltiples algoritmos (RF, XGBoost, LightGBM)
    - Feature engineering avanzado (40+ features)
    - Features de frecuencia y patrones (números calientes/fríos)
    - Calibración de probabilidades (confianza real)
    - Optimización bayesiana (mejores hiperparámetros)
    - Evolución continua
    """
    
    def __init__(
        self,
        lottery_name: str,
        model_type: str,
        max_iterations: int = 10000,
        patience: int = 100,
        use_advanced_features: bool = True,
        use_frequency_features: bool = True,
        use_calibration: bool = True,
        use_bayesian_optimization: bool = True,
        bayesian_iterations: int = 30,
        confidence_threshold: float = 0.6
    ):
        self.lottery_name = lottery_name
        self.model_type = model_type
        self.max_iterations = max_iterations
        self.patience = patience
        self.use_advanced_features = use_advanced_features
        self.use_frequency_features = use_frequency_features
        self.use_calibration = use_calibration
        self.use_bayesian_optimization = use_bayesian_optimization and BAYESIAN_AVAILABLE
        self.bayesian_iterations = bayesian_iterations
        self.confidence_threshold = confidence_threshold
        
        # Feature engineers
        self.feature_engineer = FeatureEngineer() if use_advanced_features else None
        self.freq_engineer = EnhancedFeatureEngineer(target_col=model_type) if use_frequency_features else None
        
        # Rutas
        self.models_dir = settings.MODELS_DIR
        self.variants_file = self.models_dir / f"hybrid_variants_{lottery_name}_{model_type}.json"
        
        # Variantes y modelos
        self.variants: List[HybridVariant] = []
        self.models: Dict[int, any] = {}
        
        # Cargar o inicializar
        self._load_or_initialize_variants()
        
        logger.info(f"HybridTrainer MEJORADO inicializado para {lottery_name} ({model_type})")
        logger.info(f"Feature engineering avanzado: {use_advanced_features}")
        logger.info(f"Features de frecuencia: {use_frequency_features}")
        logger.info(f"Calibración: {use_calibration}")
        logger.info(f"Optimización bayesiana: {self.use_bayesian_optimization}")
        logger.info(f"HybridTrainer inicializado para {lottery_name} ({model_type})")
        logger.info(f"Feature engineering avanzado: {use_advanced_features}")
    
    def _load_or_initialize_variants(self):
        """Carga variantes existentes o crea nuevas."""
        if self.variants_file.exists():
            with open(self.variants_file, 'r') as f:
                data = json.load(f)
                self.variants = [HybridVariant.from_dict(v) for v in data]
            logger.info(f"Cargadas {len(self.variants)} variantes híbridas")
        else:
            # Crear 3 variantes con diferentes algoritmos
            self.variants = [
                HybridVariant(
                    id=1,
                    role="PRODUCTION",
                    algorithm="RandomForest",
                    accuracy=0.0,
                    f1_score=0.0,
                    hyperparameters={
                        'n_estimators': 200,
                        'max_depth': 6,
                        'min_samples_split': 5
                    },
                    iterations_trained=0,
                    last_improvement=0,
                    created_at=datetime.now().isoformat()
                ),
                HybridVariant(
                    id=2,
                    role="EXPERIMENTAL_1",
                    algorithm="RandomForest",  # Usar RF en lugar de XGBoost para evitar problemas con clases no consecutivas
                    accuracy=0.0,
                    f1_score=0.0,
                    hyperparameters={
                        'n_estimators': 150,
                        'max_depth': 5,
                        'min_samples_split': 3
                    },
                    iterations_trained=0,
                    last_improvement=0,
                    created_at=datetime.now().isoformat()
                ),
                HybridVariant(
                    id=3,
                    role="EXPERIMENTAL_2",
                    algorithm="RandomForest",  # Usar RF en lugar de LightGBM para evitar problemas con clases no consecutivas
                    accuracy=0.0,
                    f1_score=0.0,
                    hyperparameters={
                        'n_estimators': 250,
                        'max_depth': 4,
                        'min_samples_split': 7
                    },
                    iterations_trained=0,
                    last_improvement=0,
                    created_at=datetime.now().isoformat()
                )
            ]
            logger.info("Creadas 3 variantes híbridas con diferentes algoritmos")
    
    def _save_variants(self):
        """Guarda el estado de las variantes."""
        with open(self.variants_file, 'w') as f:
            json.dump([v.to_dict() for v in self.variants], f, indent=2)
    
    def _create_model(self, variant: HybridVariant, X=None, y=None):
        """
        Crea un modelo basado en el algoritmo y configuración de la variante.
        Si se proporciona X e y, usa optimización bayesiana.
        """
        # Si hay datos y optimización bayesiana está activada, optimizar hiperparámetros
        if X is not None and y is not None and self.use_bayesian_optimization:
            logger.info(f"Optimizando hiperparámetros para variante {variant.id} ({variant.algorithm})...")
            
            try:
                optimizer = BayesianOptimizer(random_state=42)
                best_model, results = optimizer.optimize(
                    X=X,
                    y=y,
                    algorithm=variant.algorithm,
                    n_iter=self.bayesian_iterations,
                    cv=3,
                    verbose=False
                )
                
                # Actualizar hiperparámetros de la variante
                variant.hyperparameters = results['best_params']
                logger.info(f"Optimización completada: Score={results['best_score']:.4f}")
                
                return best_model
            except Exception as e:
                logger.warning(f"Error en optimización bayesiana: {e}. Usando parámetros por defecto.")
        
        # Crear modelo con hiperparámetros actuales
        if variant.algorithm == "RandomForest":
            model = RandomForestClassifier(
                n_estimators=variant.hyperparameters.get('n_estimators', 200),
                max_depth=variant.hyperparameters.get('max_depth', 6),
                min_samples_split=variant.hyperparameters.get('min_samples_split', 5),
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
        
        elif variant.algorithm == "XGBoost" and XGBOOST_AVAILABLE:
            model = xgb.XGBClassifier(
                n_estimators=variant.hyperparameters.get('n_estimators', 150),
                max_depth=variant.hyperparameters.get('max_depth', 5),
                learning_rate=variant.hyperparameters.get('learning_rate', 0.1),
                random_state=42,
                n_jobs=-1,
                eval_metric='logloss'
            )
        
        elif variant.algorithm == "LightGBM" and LIGHTGBM_AVAILABLE:
            model = lgb.LGBMClassifier(
                n_estimators=variant.hyperparameters.get('n_estimators', 180),
                max_depth=variant.hyperparameters.get('max_depth', 4),
                learning_rate=variant.hyperparameters.get('learning_rate', 0.05),
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
        
        else:
            # Fallback a RandomForest
            logger.warning(f"Algoritmo {variant.algorithm} no disponible, usando RandomForest")
            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
        
        # Aplicar calibración si está activada
        if self.use_calibration:
            # Ajustar CV según tamaño de datos
            cv_folds = 3
            if X is not None and y is not None:
                # Calcular el mínimo de ejemplos por clase
                unique, counts = np.unique(y, return_counts=True)
                min_samples_per_class = counts.min()
                # Ajustar folds para evitar errores
                if min_samples_per_class < 3:
                    cv_folds = 2
                elif min_samples_per_class < 5:
                    cv_folds = 2
            
            model = CalibratedModelWrapper(
                base_model=model,
                method='sigmoid',
                cv=cv_folds
            )
            variant.is_calibrated = True
            variant.confidence_threshold = self.confidence_threshold
        
        return model
    
    def _get_production_variant(self) -> HybridVariant:
        """Obtiene la variante en producción."""
        for v in self.variants:
            if v.role == "PRODUCTION":
                return v
        return self.variants[0]
    
    def _get_experimental_variants(self) -> List[HybridVariant]:
        """Obtiene las variantes experimentales."""
        return [v for v in self.variants if v.role.startswith("EXPERIMENTAL")]
    
    def _evaluate_variant(self, variant: HybridVariant, model, X_test, y_test) -> Tuple[float, float]:
        """Evalúa una variante."""
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='macro')
        return accuracy, f1
    
    def _mutate_variant(self, variant: HybridVariant) -> HybridVariant:
        """Crea una mutación de una variante experimental."""
        if variant.algorithm == "RandomForest":
            new_params = {
                'n_estimators': np.random.choice([100, 150, 200, 250, 300]),
                'max_depth': np.random.choice([4, 5, 6, 7, 8]),
                'min_samples_split': np.random.choice([2, 3, 5, 7, 10])
            }
        elif variant.algorithm == "XGBoost":
            new_params = {
                'n_estimators': np.random.choice([100, 150, 200, 250]),
                'max_depth': np.random.choice([3, 4, 5, 6, 7]),
                'learning_rate': np.random.choice([0.01, 0.05, 0.1, 0.2])
            }
        elif variant.algorithm == "LightGBM":
            new_params = {
                'n_estimators': np.random.choice([100, 150, 200, 250]),
                'max_depth': np.random.choice([3, 4, 5, 6]),
                'learning_rate': np.random.choice([0.01, 0.05, 0.1, 0.15])
            }
        else:
            new_params = variant.hyperparameters.copy()
        
        return HybridVariant(
            id=variant.id,
            role=variant.role,
            algorithm=variant.algorithm,
            accuracy=0.0,
            f1_score=0.0,
            hyperparameters=new_params,
            iterations_trained=0,
            last_improvement=0,
            created_at=datetime.now().isoformat()
        )
    
    def _promote_variant(self, experimental_id: int):
        """Promueve una variante experimental a producción."""
        production = self._get_production_variant()
        experimental = next(v for v in self.variants if v.id == experimental_id)
        
        logger.info(f"🔄 PROMOCIÓN: Variante {experimental_id} ({experimental.algorithm}) "
                   f"(acc={experimental.accuracy:.4f}) supera a producción "
                   f"({production.algorithm}, acc={production.accuracy:.4f})")
        
        # Intercambiar roles
        production.role, experimental.role = experimental.role, production.role
        
        # Guardar modelo de producción
        self._save_production_model(experimental)
        
        logger.info(f"✅ Nueva producción: Variante {experimental_id} ({experimental.algorithm})")
    
    def _save_production_model(self, variant: HybridVariant):
        """Guarda el modelo de producción."""
        model_path = self.models_dir / f"modelo_{self.model_type}_{self.lottery_name.lower().replace(' ', '_')}.pkl"
        
        if variant.id in self.models:
            joblib.dump(self.models[variant.id], model_path)
            logger.info(f"Modelo de producción guardado: {model_path}")
    
    def train_hybrid(
        self,
        X,
        y,
        df_original: Optional[pd.DataFrame] = None,
        verbose: bool = True
    ) -> Tuple[any, float, float]:
        """
        Entrena usando estrategia híbrida MEJORADA con todas las optimizaciones.
        
        Args:
            X: Features básicas
            y: Target
            df_original: DataFrame original con fecha y target (para features de frecuencia)
            verbose: Mostrar progreso
        
        Returns:
            Mejor modelo, accuracy, f1-score
        """
        logger.info("="*70)
        logger.info(f"Iniciando entrenamiento híbrido MEJORADO: {self.lottery_name} ({self.model_type})")
        logger.info("="*70)
        
        # Aplicar feature engineering avanzado si está habilitado
        if self.use_advanced_features:
            logger.info("Aplicando feature engineering avanzado...")
            # Crear DataFrame temporal para feature engineering
            df_temp = pd.DataFrame(X, columns=['dia', 'mes', 'anio', 'dia_semana'])
            # Crear fecha correctamente
            df_temp['fecha'] = pd.to_datetime({
                'year': df_temp['anio'],
                'month': df_temp['mes'],
                'day': df_temp['dia']
            })
            
            # Aplicar features temporales
            df_temp = FeatureEngineer.add_temporal_features(df_temp)
            df_temp = FeatureEngineer.add_holiday_features(df_temp)
            df_temp = FeatureEngineer.add_lunar_features(df_temp)
            
            # Seleccionar features numéricas
            X_enhanced = df_temp.select_dtypes(include=[np.number]).fillna(0).values
            
            logger.info(f"Features avanzadas: {X.shape[1]} → {X_enhanced.shape[1]}")
            X = X_enhanced
        
        # Aplicar features de frecuencia si está habilitado
        if self.use_frequency_features and df_original is not None:
            logger.info("Aplicando features de frecuencia y patrones...")
            
            # Crear DataFrame con fecha y target
            df_freq = df_original.copy()
            if 'fecha' not in df_freq.columns:
                df_freq['fecha'] = pd.to_datetime(df_freq[['anio', 'mes', 'dia']])
            
            # Generar features de frecuencia
            df_freq_features = self.freq_engineer.create_all_features(
                df_freq,
                include_frequency=True,
                include_temporal=False  # Ya tenemos temporales
            )
            
            # Seleccionar solo features numéricas nuevas
            freq_cols = [col for col in df_freq_features.columns 
                        if col not in ['fecha', 'lottery', 'slug', self.model_type]
                        and col not in ['dia', 'mes', 'anio', 'dia_semana']
                        and df_freq_features[col].dtype in [np.int64, np.float64]]
            
            if freq_cols:
                X_freq = df_freq_features[freq_cols].fillna(0).values
                X = np.hstack([X, X_freq])
                logger.info(f"Features de frecuencia agregadas: {len(freq_cols)}")
                logger.info(f"Features totales: {X.shape[1]}")
        
        # Optimizar hiperparámetros iniciales si está activado
        if self.use_bayesian_optimization:
            logger.info("Optimizando hiperparámetros iniciales con búsqueda bayesiana...")
            for variant in self.variants:
                self.models[variant.id] = self._create_model(variant, X, y)
        else:
            # Inicializar modelos sin optimización
            for variant in self.variants:
                self.models[variant.id] = self._create_model(variant)
        
        best_combined_score = 0.0
        iterations_without_improvement = 0
        
        for iteration in range(1, self.max_iterations + 1):
            # Split de datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=iteration
            )
            
            # Entrenar y evaluar cada variante
            improvements = []
            
            for variant in self.variants:
                model = self.models[variant.id]
                
                # Entrenar
                model.fit(X_train, y_train)
                
                # Evaluar
                accuracy, f1 = self._evaluate_variant(variant, model, X_test, y_test)
                combined_score = (accuracy + f1) / 2
                
                # Actualizar si mejoró
                old_combined = (variant.accuracy + variant.f1_score) / 2
                if combined_score > old_combined:
                    variant.accuracy = accuracy
                    variant.f1_score = f1
                    variant.last_improvement = iteration
                    improvements.append(variant.id)
                
                variant.iterations_trained = iteration
            
            # Verificar promociones
            production = self._get_production_variant()
            prod_score = (production.accuracy + production.f1_score) / 2
            
            for exp_variant in self._get_experimental_variants():
                exp_score = (exp_variant.accuracy + exp_variant.f1_score) / 2
                if exp_score > prod_score:
                    self._promote_variant(exp_variant.id)
                    production = exp_variant
                    prod_score = exp_score
                    iterations_without_improvement = 0
            
            # Verificar mejora global
            if prod_score > best_combined_score:
                best_combined_score = prod_score
                iterations_without_improvement = 0
            else:
                iterations_without_improvement += 1
            
            # Mostrar progreso
            if verbose and iteration % 10 == 0:
                prod = self._get_production_variant()
                cal_marker = "[CAL]" if prod.is_calibrated else ""
                print(f"\r{'**' if improvements else '  '} "
                      f"{iteration}/{self.max_iterations} ({iteration/self.max_iterations*100:.1f}%) | "
                      f"{prod.algorithm[:4]}{cal_marker}: Acc={prod.accuracy:.4f} F1={prod.f1_score:.4f} | "
                      f"Best: {best_combined_score:.4f} | No-improve: {iterations_without_improvement}", end='')
            
            # Mutar experimentales
            if iteration % 200 == 0:
                for exp_variant in self._get_experimental_variants():
                    if iteration - exp_variant.last_improvement > 200:
                        logger.info(f"Mutando variante {exp_variant.id} ({exp_variant.algorithm})")
                        mutated = self._mutate_variant(exp_variant)
                        idx = self.variants.index(exp_variant)
                        self.variants[idx] = mutated
                        self.models[mutated.id] = self._create_model(mutated)
            
            # Early stopping
            if iterations_without_improvement >= self.patience:
                if verbose:
                    print(f"\n\nEarly stopping: {self.patience} iteraciones sin mejora")
                break
        
        if verbose:
            print("\n")
        
        # Guardar estado
        self._save_variants()
        
        # Retornar modelo de producción
        production = self._get_production_variant()
        self._save_production_model(production)
        
        logger.info("="*70)
        logger.info("Entrenamiento híbrido MEJORADO completado")
        logger.info(f"Algoritmo ganador: {production.algorithm}")
        logger.info(f"Calibrado: {production.is_calibrated}")
        logger.info(f"Accuracy: {production.accuracy:.4f}")
        logger.info(f"F1-Score: {production.f1_score:.4f}")
        logger.info("="*70)
        
        return self.models[production.id], production.accuracy, production.f1_score
    
    def get_variants_summary(self) -> str:
        """Retorna un resumen de las variantes."""
        lines = ["\n" + "="*70]
        lines.append(f"VARIANTES HÍBRIDAS - {self.lottery_name} ({self.model_type})")
        lines.append("="*70)
        
        for variant in sorted(self.variants, key=lambda v: (v.accuracy + v.f1_score) / 2, reverse=True):
            role_symbol = "🏆" if variant.role == "PRODUCTION" else "🧪"
            lines.append(f"\n{role_symbol} Variante #{variant.id} ({variant.role})")
            lines.append(f"   Algoritmo: {variant.algorithm}")
            lines.append(f"   Accuracy: {variant.accuracy:.4f}")
            lines.append(f"   F1-Score: {variant.f1_score:.4f}")
            lines.append(f"   Combined: {(variant.accuracy + variant.f1_score) / 2:.4f}")
            lines.append(f"   Hiperparámetros: {variant.hyperparameters}")
            lines.append(f"   Iteraciones: {variant.iterations_trained}")
            lines.append(f"   Última mejora: iter {variant.last_improvement}")
        
        lines.append("="*70)
        return "\n".join(lines)


def entrenar_hibrido(
    X,
    y_result,
    y_series,
    lottery_name: str,
    df_original: Optional[pd.DataFrame] = None,
    max_iterations: int = 10000,
    patience: int = 100,
    use_advanced_features: bool = True,
    use_frequency_features: bool = True,
    use_calibration: bool = True,
    use_bayesian_optimization: bool = True,
    bayesian_iterations: int = 30,
    confidence_threshold: float = 0.6,
    verbose: bool = True
) -> Dict:
    """
    Función de conveniencia para entrenar ambos modelos híbridamente con TODAS las mejoras.
    
    Args:
        X: Features básicas
        y_result: Target para modelo result
        y_series: Target para modelo series
        lottery_name: Nombre de la lotería
        df_original: DataFrame original con fecha y targets (para features de frecuencia)
        max_iterations: Iteraciones máximas
        patience: Paciencia para early stopping
        use_advanced_features: Usar features avanzadas (40+)
        use_frequency_features: Usar features de frecuencia y patrones
        use_calibration: Usar calibración de probabilidades
        use_bayesian_optimization: Usar optimización bayesiana
        bayesian_iterations: Iteraciones para optimización bayesiana
        confidence_threshold: Umbral de confianza para calibración
        verbose: Mostrar progreso
    
    Returns:
        Dict con modelos, accuracies y f1-scores
    """
    results = {}
    
    # Entrenar modelo result
    logger.info(f"\n{'='*70}")
    logger.info(f"Entrenando modelo RESULT para {lottery_name}")
    logger.info('='*70)
    
    # Preparar DataFrame para result
    df_result = None
    if df_original is not None and use_frequency_features:
        df_result = df_original.copy()
        df_result['result'] = y_result
    
    trainer_result = HybridTrainer(
        lottery_name=lottery_name,
        model_type="result",
        max_iterations=max_iterations,
        patience=patience,
        use_advanced_features=use_advanced_features,
        use_frequency_features=use_frequency_features,
        use_calibration=use_calibration,
        use_bayesian_optimization=use_bayesian_optimization,
        bayesian_iterations=bayesian_iterations,
        confidence_threshold=confidence_threshold
    )
    
    model_result, acc_result, f1_result = trainer_result.train_hybrid(
        X, y_result, df_original=df_result, verbose=verbose
    )
    
    if verbose:
        print(trainer_result.get_variants_summary())
    
    results['result'] = {
        'model': model_result,
        'accuracy': acc_result,
        'f1_score': f1_result,
        'trainer': trainer_result
    }
    
    # Entrenar modelo series
    logger.info(f"\n{'='*70}")
    logger.info(f"Entrenando modelo SERIES para {lottery_name}")
    logger.info('='*70)
    
    # Preparar DataFrame para series
    df_series = None
    if df_original is not None and use_frequency_features:
        df_series = df_original.copy()
        df_series['series'] = y_series
    
    trainer_series = HybridTrainer(
        lottery_name=lottery_name,
        model_type="series",
        max_iterations=max_iterations,
        patience=patience,
        use_advanced_features=use_advanced_features,
        use_frequency_features=use_frequency_features,
        use_calibration=use_calibration,
        use_bayesian_optimization=use_bayesian_optimization,
        bayesian_iterations=bayesian_iterations,
        confidence_threshold=confidence_threshold
    )
    
    model_series, acc_series, f1_series = trainer_series.train_hybrid(
        X, y_series, df_original=df_series, verbose=verbose
    )
    
    if verbose:
        print(trainer_series.get_variants_summary())
    
    results['series'] = {
        'model': model_series,
        'accuracy': acc_series,
        'f1_score': f1_series,
        'trainer': trainer_series
    }
    
    return results


if __name__ == "__main__":
    print("Sistema de Entrenamiento Híbrido")
    print("Combina múltiples algoritmos con evolución continua")
