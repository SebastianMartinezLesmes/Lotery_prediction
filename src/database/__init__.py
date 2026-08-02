"""
Módulo de acceso a datos — Neon PostgreSQL.

Expone la conexión y el repositorio para uso en otros módulos.
"""
from src.database.connection import NeonConnection
from src.database.repository import LotteriaRepository

__all__ = ["NeonConnection", "LotteriaRepository"]
