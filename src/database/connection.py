"""
Conexión a Neon PostgreSQL usando psycopg2.
Lee DATABASE_URL desde el archivo .env.
"""
import os
import time
import psycopg2
from typing import Optional
from dotenv import load_dotenv

from src.core.logger import LoggerManager

load_dotenv()

logger = LoggerManager.get_logger("neon_connection")

# Segundos máximos esperando que Neon acepte la conexión TCP.
# Neon puede tener cold-start de ~5 s; 15 s da margen sin bloquear el job.
_CONNECT_TIMEOUT_SECONDS = 15

# Política de reintentos para errores transitorios de red/cold-start.
_MAX_RETRIES = 3
_RETRY_BACKOFF = [2, 5, 10]   # segundos entre intentos 1→2, 2→3, 3→falla


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
        """Abre (o reutiliza) la conexión a Neon.

        Reintenta hasta _MAX_RETRIES veces con backoff exponencial para
        tolerar cold-starts de Neon y errores transitorios de red.
        """
        if self._connection is not None and not self._connection.closed:
            return self._connection

        last_exc: Exception = RuntimeError("No se intentó conectar")
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                # connect_timeout se añade como parámetro DSN; si la URL ya lo
                # trae no se duplica porque psycopg2 usa el último valor.
                self._connection = psycopg2.connect(
                    self._database_url,
                    connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                )
                logger.info(
                    f"Conexión a Neon PostgreSQL establecida "
                    f"(intento {attempt}/{_MAX_RETRIES})."
                )
                return self._connection
            except psycopg2.OperationalError as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF[attempt - 1]
                    logger.warning(
                        f"Error conectando a Neon (intento {attempt}/{_MAX_RETRIES}): {e} "
                        f"— reintentando en {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Error conectando a Neon después de {_MAX_RETRIES} intentos: {e}"
                    )

        raise last_exc

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
