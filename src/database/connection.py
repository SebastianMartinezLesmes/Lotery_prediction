"""
Conexión a Neon PostgreSQL usando psycopg2.
Lee DATABASE_URL desde el archivo .env.
"""
import os
import psycopg2
from typing import Optional
from dotenv import load_dotenv

from src.core.logger import LoggerManager

load_dotenv()

logger = LoggerManager.get_logger("neon_connection", "log_loteria.log")


class NeonConnection:
    """Gestiona la conexión a Neon PostgreSQL."""

    def __init__(self):
        self._connection: Optional[psycopg2.extensions.connection] = None
        self._database_url: str = os.getenv("DATABASE_URL", "")
        if not self._database_url:
            raise ValueError(
                "DATABASE_URL no está configurada. "
                "Agrega DATABASE_URL en el archivo .env"
            )

    def connect(self) -> psycopg2.extensions.connection:
        """Abre (o reutiliza) la conexión a Neon."""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(self._database_url)
                logger.info("Conexión a Neon PostgreSQL establecida.")
            except psycopg2.OperationalError as e:
                logger.error(f"Error al conectar a Neon: {e}")
                raise
        return self._connection

    def close(self) -> None:
        """Cierra la conexión si está abierta."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
            logger.info("Conexión a Neon PostgreSQL cerrada.")

    def get_connection(self) -> psycopg2.extensions.connection:
        """Retorna la conexión activa, abriéndola si es necesario."""
        return self.connect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self._connection and not self._connection.closed:
                self._connection.rollback()
        self.close()
        return False
