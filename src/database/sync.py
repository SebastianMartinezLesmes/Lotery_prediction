"""
Orquestador de sincronización entre SuperAstro y Neon PostgreSQL.

Uso:
    from src.database.sync import synchronize_database
    synchronize_database()                          # todas las loterías
    synchronize_database(filtro_loteria="ASTRO LUNA")  # una sola
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

from src.core.logger import LoggerManager
from src.database.repository import LotteriaRepository
from src.database.connection import NeonConnection

logger = LoggerManager.get_logger("neon_sync", "log_loteria.log")

# Loterías disponibles en SuperAstro
LOTERIAS_DISPONIBLES = ["ASTRO SOL", "ASTRO LUNA"]


def synchronize_database(filtro_loteria: Optional[str] = None) -> int:
    """
    Orquesta la sincronización completa entre SuperAstro y Neon PostgreSQL.

    1. Determina qué loterías sincronizar (todas o una sola).
    2. Para cada lotería llama a SuperAstroScraper.sincronizar_con_neon().
    3. Loguea inicio, fin y métricas.

    Args:
        filtro_loteria: Si se pasa, sólo sincroniza las loterías cuyo nombre
                        contenga ese texto (insensible a mayúsculas).

    Returns:
        Total de registros insertados/actualizados en Neon.
    """
    # Importación local para evitar ciclos
    from src.api.superastro_scraper import SuperAstroScraper

    inicio = time.time()
    ahora  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("=" * 70)
    logger.info(f"SINCRONIZACIÓN NEON — inicio: {ahora}")
    logger.info("=" * 70)

    # ── Seleccionar loterías ──────────────────────────────────────────
    if filtro_loteria:
        loterias = [
            l for l in LOTERIAS_DISPONIBLES
            if filtro_loteria.upper() in l.upper()
        ]
        if not loterias:
            logger.warning(
                f"No se encontraron loterías que coincidan con '{filtro_loteria}'. "
                f"Disponibles: {LOTERIAS_DISPONIBLES}"
            )
            return 0
    else:
        loterias = LOTERIAS_DISPONIBLES

    logger.info(f"Loterías a sincronizar: {loterias}")

    # ── Inicializar repositorio y scraper ────────────────────────────
    try:
        conn       = NeonConnection()
        repository = LotteriaRepository(conn)
        scraper    = SuperAstroScraper()
    except Exception as e:
        logger.error(f"Error inicializando componentes: {e}")
        raise

    # ── Sincronizar cada lotería ─────────────────────────────────────
    total_registros = 0
    metricas: dict[str, int] = {}

    for loteria in loterias:
        try:
            n = scraper.sincronizar_con_neon(loteria, repository)
            metricas[loteria] = n
            total_registros  += n
            logger.info(f"  {loteria}: {n} registros sincronizados")
        except Exception as e:
            logger.error(f"  {loteria}: error durante sincronización — {e}")
            metricas[loteria] = -1  # -1 indica fallo

    # ── Resumen ──────────────────────────────────────────────────────
    duracion = time.time() - inicio
    logger.info("=" * 70)
    logger.info("RESUMEN SINCRONIZACIÓN")
    for lot, n in metricas.items():
        estado = f"{n} registros" if n >= 0 else "ERROR"
        logger.info(f"  {lot}: {estado}")
    logger.info(f"Total registros: {total_registros}")
    logger.info(f"Duración: {duracion:.2f}s")
    logger.info("=" * 70)

    # ── Cerrar conexión ──────────────────────────────────────────────
    try:
        conn.close()
    except Exception:
        pass

    return total_registros
