"""
Sistema de Entrenamiento Evolutivo.
Mantiene múltiples variantes de modelos que compiten y evolucionan.
"""
import os
import json
import joblib
import numpy as np

from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from sklearn.ensemble import RandomForestClassifier
from src.core.logger import LoggerManager
from src.core.config import settings

logger = LoggerManager.get_logger("evolutionary_training", "evolutionary.log")


@dataclass
class ModelVariant:
    """Representa una variante de modelo."""
    id: int
    role: str  # "PRODUCTION", "EXPERIMENTAL_1", "EXPERIMENTAL_2"
    accuracy: float
    f1_score: float
    n_estimators: int
    max_depth: int
    min_samples_split: int
    random_state: int
    iterations_trained: int
    last_improvement: int
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelVariant':
        return cls(**data)


class EvolutionaryTrainer:
    """
    Entrenador evolutivo que mantiene múltiples variantes de modelos.
    
    Estrategia:
    1. Variante #1 (PRODUCTION): Mejor modelo, usado para predicciones
    2. Variante #2 (EXPERIMENTAL_1): Explora configuraciones alternativas
    3. Variante #3 (EXPERIMENTAL_2): Explora configuraciones alternativas
    
    Si una experimental supera a production, se intercambian roles.
    """
    
    def __init__(
        self,
        lottery_name: str,
        model_type: str,  # "result" o "series"
        max_iterations: int = 10000,
        patience: int = 100
    ):
        self.lottery_name = lottery_name
        self.model_type = model_type
        self.max_iterations = max_iterations
        self.patience = patience
        
        # Rutas
        self.models_dir = settings.MODELS_DIR
        self.variants_file = self.models_dir / f"variants_{lottery_name}_{model_type}.json"
        
        # Variantes
        self.variants: List[ModelVariant] = []
        self.models: Dict[int, RandomForestClassifier] = {}
        
        # Cargar o inicializar variantes
        self._load_or_initialize_variants()
        
        logger.info(f"EvolutionaryTrainer inicializado para {lottery_name} ({model_type})")
    
    def _load_or_initialize_variants(self):
        """Carga variantes existentes o crea nuevas."""
        
        if self.variants_file.exists():
            with open(self.variants_file, 'r') as f:
                data = json.load(f)
                self.variants = [ModelVariant.from_dict(v) for v in data]

            logger.info(f"Cargadas {len(self.variants)} variantes existentes")

        else:
            self.variants = []

            for variant_cfg in settings.MODEL_VARIANTS:
                self.variants.append(
                    ModelVariant(
                        accuracy=0.0,
                        f1_score=0.0,
                        iterations_trained=0,
                        last_improvement=0,
                        created_at=datetime.now().isoformat(),
                        **variant_cfg
                    )
                )

            logger.info(f"Creadas {len(self.variants)} variantes iniciales")
    
    def _save_variants(self):
        """Guarda el estado de las variantes."""
        with open(self.variants_file, 'w') as f:
            json.dump([v.to_dict() for v in self.variants], f, indent=2)
    
    def _get_production_variant(self) -> ModelVariant:
        """Obtiene la variante en producción."""
        for v in self.variants:
            if v.role == "PRODUCTION":
                return v
        return self.variants[0]  # Fallback
    
    def _get_experimental_variants(self) -> List[ModelVariant]:
        """Obtiene las variantes experimentales."""
        return [v for v in self.variants if v.role.startswith("EXPERIMENTAL")]
    
    def _create_model(self, variant: ModelVariant) -> RandomForestClassifier:
        """Crea un modelo basado en la configuración de la variante."""
        return RandomForestClassifier(
            n_estimators=variant.n_estimators,
            max_depth=variant.max_depth,
            min_samples_split=variant.min_samples_split,
            class_weight='balanced',
            random_state=variant.random_state,
            n_jobs=-1
        )
    
    def _evaluate_variant(
        self,
        variant: ModelVariant,
        model: RandomForestClassifier,
        X_test,
        y_test
    ) -> Tuple[float, float]:
        """Evalúa una variante y retorna accuracy y f1-score."""
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='macro')
        return accuracy, f1
    
    def _mutate_variant(self, variant: ModelVariant) -> ModelVariant:
        """
        Crea una mutación de una variante experimental.
        Cambia ligeramente los hiperparámetros para explorar.
        """
        mutations = {
            'n_estimators': [100, 150, 200, 250, 300],
            'max_depth': [3, 4, 5, 6, 7, 8],
            'min_samples_split': [2, 3, 5, 7, 10]
        }
        
        new_variant = ModelVariant(
            id=variant.id,
            role=variant.role,
            accuracy=0.0,
            f1_score=0.0,
            n_estimators=np.random.choice(MODEL_MUTATION_RANGES['n_estimators']),
            max_depth=np.random.choice(MODEL_MUTATION_RANGES['max_depth']),
            min_samples_split=np.random.choice(MODEL_MUTATION_RANGES['min_samples_split']),
            random_state=np.random.randint(*MODEL_RANDOM_STATE_RANGE),
            iterations_trained=0,
            last_improvement=0,
            created_at=datetime.now().isoformat()
        )
        
        logger.info(
            f"Mutación creada para variante {variant.id}: "
            f"n_est={new_variant.n_estimators}, "
            f"depth={new_variant.max_depth}, "
            f"split={new_variant.min_samples_split}"
        )
        
        return new_variant
    
    def _promote_variant(self, experimental_id: int):
        """
        Promueve una variante experimental a producción.
        La actual producción se convierte en experimental.
        """
        production = self._get_production_variant()
        experimental = next(v for v in self.variants if v.id == experimental_id)
        
        logger.info(f"🔄 PROMOCIÓN: Variante {experimental_id} "
                   f"(acc={experimental.accuracy:.4f}) "
                   f"supera a producción (acc={production.accuracy:.4f})")
        
        # Intercambiar roles
        old_prod_role = production.role
        production.role = experimental.role
        experimental.role = old_prod_role
        
        # Guardar modelo de producción
        self._save_production_model(experimental)
        
        logger.info(f"✅ Nueva producción: Variante {experimental_id}")
    
    def _save_production_model(self, variant: ModelVariant):
        """Guarda el modelo de producción en el archivo .pkl principal."""
        model_path = self.models_dir / f"modelo_{self.model_type}_{self.lottery_name.lower().replace(' ', '_')}.pkl"
        
        if variant.id in self.models:
            joblib.dump(self.models[variant.id], model_path)
            logger.info(f"Modelo de producción guardado: {model_path}")
    
    def train_evolutionary(
        self,
        X,
        y,
        verbose: bool = True
    ) -> Tuple[RandomForestClassifier, float, float]:
        """
        Entrena usando estrategia evolutiva.
        
        Returns:
            Mejor modelo, accuracy, f1-score
        """
        logger.info("="*70)
        logger.info(f"Iniciando entrenamiento evolutivo: {self.lottery_name} ({self.model_type})")
        logger.info("="*70)
        
        # Inicializar modelos para cada variante
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
            
            # Verificar si alguna experimental supera a producción
            production = self._get_production_variant()
            prod_score = (production.accuracy + production.f1_score) / 2
            
            for exp_variant in self._get_experimental_variants():
                exp_score = (exp_variant.accuracy + exp_variant.f1_score) / 2
                if exp_score > prod_score:
                    self._promote_variant(exp_variant.id)
                    production = exp_variant  # Actualizar referencia
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
                print(f"\r{'**' if improvements else '  '} "
                      f"{iteration}/{self.max_iterations} ({iteration/self.max_iterations*100:.1f}%) | "
                      f"Prod: Acc={prod.accuracy:.4f} F1={prod.f1_score:.4f} | "
                      f"Best: {best_combined_score:.4f} | "
                      f"No-improve: {iterations_without_improvement}", end='')
            
            # Mutar experimentales si llevan mucho sin mejorar
            if iteration % 200 == 0:
                for exp_variant in self._get_experimental_variants():
                    if iteration - exp_variant.last_improvement > 200:
                        logger.info(f"Mutando variante {exp_variant.id} (sin mejora en 200 iter)")
                        mutated = self._mutate_variant(exp_variant)
                        # Actualizar variante
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
        
        # Guardar estado final
        self._save_variants()
        
        # Retornar modelo de producción
        production = self._get_production_variant()
        self._save_production_model(production)
        
        logger.info("="*70)
        logger.info("Entrenamiento evolutivo completado")
        logger.info(f"Modelo de producción: Variante {production.id}")
        logger.info(f"Accuracy: {production.accuracy:.4f}")
        logger.info(f"F1-Score: {production.f1_score:.4f}")
        logger.info(f"Iteraciones: {iteration}")
        logger.info("="*70)
        
        return self.models[production.id], production.accuracy, production.f1_score
    
    def get_variants_summary(self) -> str:
        """Retorna un resumen de las variantes actuales."""
        lines = ["\n" + "="*70]
        lines.append(f"VARIANTES - {self.lottery_name} ({self.model_type})")
        lines.append("="*70)
        
        for variant in sorted(self.variants, key=lambda v: (v.accuracy + v.f1_score) / 2, reverse=True):
            role_symbol = "🏆" if variant.role == "PRODUCTION" else "🧪"
            lines.append(f"\n{role_symbol} Variante #{variant.id} ({variant.role})")
            lines.append(f"   Accuracy: {variant.accuracy:.4f}")
            lines.append(f"   F1-Score: {variant.f1_score:.4f}")
            lines.append(f"   Combined: {(variant.accuracy + variant.f1_score) / 2:.4f}")
            lines.append(f"   Config: n_est={variant.n_estimators}, "
                        f"depth={variant.max_depth}, split={variant.min_samples_split}")
            lines.append(f"   Iteraciones: {variant.iterations_trained}")
            lines.append(f"   Última mejora: iter {variant.last_improvement}")
        
        lines.append("="*70)
        return "\n".join(lines)


    def entrenar_evolutivo(
        X,
        y_result,
        y_series,
        lottery_name: str,
        max_iterations: int = EVOLUTIONARY_MAX_ITERATIONS,
        patience: int = EVOLUTIONARY_PATIENCE,
        verbose: bool = True
    ) -> Dict:
        """
        Función de conveniencia para entrenar ambos modelos (result y series) evolutivamente.
        
        Returns:
            Dict con modelos, accuracies y f1-scores
        """
        results = {}
        
        # Entrenar modelo result
        logger.info(f"\n{LOG_SEPARATOR}")
        logger.info(f"Entrenando modelo RESULT para {lottery_name}")
        logger.info(LOG_SEPARATOR)
        
        trainer_result = EvolutionaryTrainer(
            lottery_name=lottery_name,
            model_type="result",
            max_iterations=max_iterations,
            patience=patience
        )
        
        model_result, acc_result, f1_result = trainer_result.train_evolutionary(
            X, y_result, verbose=verbose
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
        logger.info(f"\n{LOG_SEPARATOR}")
        logger.info(f"Entrenando modelo SERIES para {lottery_name}")
        logger.info(LOG_SEPARATOR)
        
        trainer_series = EvolutionaryTrainer(
            lottery_name=lottery_name,
            model_type="series",
            max_iterations=max_iterations,
            patience=patience
        )
        
        model_series, acc_series, f1_series = trainer_series.train_evolutionary(
            X, y_series, verbose=verbose
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
    print("Sistema de Entrenamiento Evolutivo")
    print("Este módulo debe ser importado y usado desde main.py o scripts de entrenamiento")
