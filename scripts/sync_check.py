"""
sync_check.py — Script de verificación de sincronización Neon.

Uso:
    FILTRO="luna" python scripts/sync_check.py
    python scripts/sync_check.py          # todas las loterías

Sale con código 1 si:
  - hubo excepción durante la sincronización
  - filas parseadas == 0
  - MAX(fecha) de cualquier lotería es anterior a hoy - 3 días
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

# Asegura que el raíz del proyecto está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logger import LoggerManager
from src.database.sync import synchronize_database
from src.database.connection import NeonConnection
from src.database.repository import LotteriaRepository

logger = LoggerManager.get_logger("sync_check")

LOTERIAS = ["ASTRO SOL", "ASTRO LUNA"]


def get_max_fecha(repository: LotteriaRepository, loteria: str):
    """Retorna MAX(fecha) para la lotería dada, o None si no hay registros."""
    return repository.get_last_date(loteria)


def main() -> int:
    filtro = os.environ.get("FILTRO", "").strip()

    # ── Sincronización ────────────────────────────────────────────────
    total = 0
    error_sync = None
    try:
        if filtro:
            logger.info(f"Sincronizando con filtro: {filtro}")
            total = synchronize_database(filtro_loteria=filtro)
        else:
            logger.info("Sincronizando todas las loterías")
            total = synchronize_database()
    except Exception as exc:
        logger.error(f"Error durante sincronización: {exc}")
        error_sync = exc

    print(f"TOTAL_REGISTROS={total}")

    # ── Verificar freshness ───────────────────────────────────────────
    hoy = date.today()
    umbral = hoy - timedelta(days=3)
    loterias_a_verificar = (
        [l for l in LOTERIAS if filtro.upper() in l]
        if filtro
        else LOTERIAS
    )

    print("")
    print(f"{'Lotería':<20} | {'Última fecha':<12} | {'Estado'}")
    print("-" * 55)

    fechas_vencidas = []
    conn = None
    try:
        conn = NeonConnection()
        repo = LotteriaRepository(conn)
        for loteria in loterias_a_verificar:
            max_fecha = get_max_fecha(repo, loteria)
            if max_fecha is None:
                estado = "SIN DATOS"
                fechas_vencidas.append(loteria)
            elif max_fecha < umbral:
                estado = f"DESACTUALIZADO (umbral: hoy-3d = {umbral})"
                fechas_vencidas.append(loteria)
            else:
                estado = "OK"
            print(f"{loteria:<20} | {str(max_fecha) if max_fecha else 'None':<12} | {estado}")
    except Exception as exc:
        logger.error(f"Error verificando fechas: {exc}")
        # Si no podemos conectar para verificar, ya el error de sync capturado arriba lo indica
        if error_sync is None:
            error_sync = exc
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    print("")

    # ── Decisión de exit code ─────────────────────────────────────────
    if error_sync is not None:
        logger.error("Saliendo con código 1: hubo excepción durante sincronización.")
        return 1

    if total == 0:
        logger.warning("Saliendo con código 1: 0 filas parseadas/sincronizadas.")
        return 1

    if fechas_vencidas:
        logger.error(
            f"Saliendo con código 1: MAX(fecha) desactualizada para: {fechas_vencidas}"
        )
        return 1

    logger.info("Sincronización verificada correctamente. Saliendo con código 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
