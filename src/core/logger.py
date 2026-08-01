"""
Logger centralizado - solo consola, sin archivos .log.
"""
import sys
import logging
from typing import Optional
from src.core.config import settings


class LoggerManager:
    """Gestor centralizado de loggers (solo stdout)."""

    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file: Optional[str] = None,   # ignorado, se mantiene por compatibilidad
        level: Optional[str] = None,
    ) -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        log_level = getattr(logging, level or settings.LOG_LEVEL, logging.INFO)
        logger.setLevel(log_level)

        if not logger.handlers:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(log_level)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        cls._loggers[name] = logger
        return logger


def get_main_logger() -> logging.Logger:
    return LoggerManager.get_logger("lottery_system")


def get_training_logger() -> logging.Logger:
    return LoggerManager.get_logger("training")


def get_api_logger() -> logging.Logger:
    return LoggerManager.get_logger("api")


def get_prediction_logger() -> logging.Logger:
    return LoggerManager.get_logger("prediction")
