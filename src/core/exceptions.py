"""
Excepciones personalizadas para el sistema de predicción de lotería.
"""

class LotteryPredictionError(Exception):
    """Excepción base para errores del sistema."""
    pass


class DataValidationError(LotteryPredictionError):
    """Error en la validación de datos."""
    pass


class ModelNotFoundError(LotteryPredictionError):
    """Modelo no encontrado."""
    pass


class ModelTrainingError(LotteryPredictionError):
    """Error durante el entrenamiento del modelo."""
    pass


class APIError(LotteryPredictionError):
    """Error al consumir la API externa."""
    pass


class ExcelError(LotteryPredictionError):
    """Error al leer o escribir archivos Excel."""
    pass


class InsufficientDataError(LotteryPredictionError):
    """Datos insuficientes para entrenar o predecir."""
    pass
