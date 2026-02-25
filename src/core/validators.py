"""
Validadores de datos y funciones de utilidad para validación.
"""
from typing import List, Optional
import pandas as pd
from src.models.schemas import LotteryResult
from src.core.exceptions import DataValidationError, InsufficientDataError
from src.core.logger import get_main_logger

logger = get_main_logger()


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
    """
    Valida que un DataFrame contenga las columnas requeridas.
    
    Args:
        df: DataFrame a validar
        required_columns: Lista de columnas requeridas
    
    Raises:
        DataValidationError: Si faltan columnas o el DataFrame está vacío
    """
    if df.empty:
        raise DataValidationError("El DataFrame está vacío")
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise DataValidationError(
            f"Faltan columnas requeridas: {', '.join(missing_columns)}"
        )
    
    logger.info(f"DataFrame validado correctamente con {len(df)} filas")


def validate_lottery_results(results: List[dict]) -> List[LotteryResult]:
    """
    Valida una lista de resultados de lotería usando Pydantic.
    
    Args:
        results: Lista de diccionarios con resultados
    
    Returns:
        Lista de objetos LotteryResult validados
    
    Raises:
        DataValidationError: Si algún resultado no es válido
    """
    validated_results = []
    errors = []
    
    for idx, result in enumerate(results):
        try:
            validated = LotteryResult(**result)
            validated_results.append(validated)
        except Exception as e:
            errors.append(f"Resultado {idx}: {str(e)}")
    
    if errors:
        error_msg = "\n".join(errors)
        logger.error(f"Errores de validación:\n{error_msg}")
        raise DataValidationError(f"Errores en validación de resultados:\n{error_msg}")
    
    logger.info(f"Validados {len(validated_results)} resultados correctamente")
    return validated_results


def validate_training_data(
    X: pd.DataFrame,
    y: pd.Series,
    min_samples: int = 50
) -> None:
    """
    Valida que los datos de entrenamiento sean suficientes.
    
    Args:
        X: Features de entrenamiento
        y: Target de entrenamiento
        min_samples: Número mínimo de muestras requeridas
    
    Raises:
        InsufficientDataError: Si no hay suficientes datos
        DataValidationError: Si hay inconsistencias en los datos
    """
    if len(X) < min_samples:
        raise InsufficientDataError(
            f"Datos insuficientes: {len(X)} muestras (mínimo: {min_samples})"
        )
    
    if len(X) != len(y):
        raise DataValidationError(
            f"Inconsistencia: X tiene {len(X)} filas pero y tiene {len(y)}"
        )
    
    if X.isnull().any().any():
        null_cols = X.columns[X.isnull().any()].tolist()
        raise DataValidationError(
            f"Valores nulos encontrados en columnas: {', '.join(null_cols)}"
        )
    
    logger.info(f"Datos de entrenamiento validados: {len(X)} muestras")


def validate_model_path(path: str) -> None:
    """
    Valida que la ruta del modelo tenga el formato correcto.
    
    Args:
        path: Ruta del modelo
    
    Raises:
        DataValidationError: Si la ruta no es válida
    """
    if not path.endswith('.pkl'):
        raise DataValidationError(
            f"La ruta del modelo debe terminar en .pkl: {path}"
        )
    
    if not any(x in path for x in ['result', 'series']):
        raise DataValidationError(
            f"La ruta del modelo debe contener 'result' o 'series': {path}"
        )
