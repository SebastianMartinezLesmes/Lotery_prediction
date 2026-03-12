"""
Sistema de logging mejorado con soporte para múltiples niveles y handlers.
"""
import sys
import logging

from pathlib import Path
from typing import Optional
from src.core.config import settings


class LoggerManager:
    """Gestor centralizado de loggers."""
    
    _loggers: dict[str, logging.Logger] = {}
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file: Optional[str] = None,
        level: Optional[str] = None
    ) -> logging.Logger:
        """
        Obtiene o crea un logger configurado.
        
        Args:
            name: Nombre del logger
            log_file: Nombre del archivo de log (opcional)
            level: Nivel de logging (opcional, usa settings.LOG_LEVEL por defecto)
        
        Returns:
            Logger configurado
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        log_level = getattr(logging, level or settings.LOG_LEVEL, logging.INFO)
        logger.setLevel(log_level)
        
        # Evitar duplicación de handlers
        if logger.handlers:
            return logger
        
        # Formato de log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler de consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler de archivo si se especifica
        if log_file:
            file_path = settings.LOGS_DIR / log_file
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


# Loggers predefinidos
def get_main_logger() -> logging.Logger:
    """Logger principal del sistema."""
    return LoggerManager.get_logger("lottery_system", "log_loteria.log")


def get_training_logger() -> logging.Logger:
    """Logger para entrenamiento de modelos."""
    return LoggerManager.get_logger("training", "training.log")


def get_api_logger() -> logging.Logger:
    """Logger para operaciones de API."""
    return LoggerManager.get_logger("api", "api.log")


def get_prediction_logger() -> logging.Logger:
    """Logger para predicciones."""
    return LoggerManager.get_logger("prediction", "prediction.log")
