"""
sync_check.py — Script de sincronización Neon.

Uso:
    FILTRO="luna" python scripts/sync_check.py
    python scripts/sync_check.py          # todas las loterías

Sale con código 1 únicamente si:
  - no se pudo conectar a Neon
  - hubo excepción durante la sincronización

Sale con código 0 (éxito) si:
  - la sincronización se completó, incluyendo el caso en que ya estaba al día
    y se sincronizaron 0 registros nuevos (normal en días sin sorteo o con DB
    ya actualizada).
"""
from __future__ import annotations

import os
import sys
from datetime import date

# Asegura que el raíz del proyecto está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logger import LoggerManager
from src.database.sync import synchronize_database
from src.database.connection import NeonConnection
from src.database.repository import LotteriaRepository

logger = LoggerManager.get_logger("sync_check")

LOTERIAS = ["ASTRO SOL", "ASTRO LUNA"]


def main() -> int:
    filtro = os.environ.get("FILTRO", "").strip()

    # ── Abrir UNA conexión para todo el script ────────────────────────
    conn = None
    try:
        conn = NeonConnection()
        repo = LotteriaRepository(conn)
    except Exception as exc:
        logger.error(f"No se pudo conectar a Neon: {exc}")
        print("TOTAL_REGISTROS=0")
        return 1

    # ── Sincronización ────────────────────────────────────────────────
    total = 0
    try:
        if filtro:
            logger.info(f"Sincronizando con filtro: {filtro}")
            total = synchronize_database(filtro_loteria=filtro, repository=repo)
        else:
            logger.info("Sincronizando todas las loterías")
            total = synchronize_database(repository=repo)
    except Exception as exc:
        logger.error(f"Error durante sincronización: {exc}")
        print("TOTAL_REGISTROS=0")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print(f"TOTAL_REGISTROS={total}")

    # ── Tabla informativa de estado ───────────────────────────────────
    # Solo para el resumen de Actions; no condiciona el exit code.
    try:
        conn2 = NeonConnection()
        repo2 = LotteriaRepository(conn2)
        loterias_a_mostrar = (
            [l for l in LOTERIAS if filtro.upper() in l] if filtro else LOTERIAS
        )

        print("")
        print(f"{'Lotería':<20} | {'Última fecha':<12} | {'Estado'}")
        print("-" * 55)

        for loteria in loterias_a_mostrar:
            max_fecha = repo2.get_last_date(loteria)
            estado = "OK" if max_fecha else "SIN DATOS"
            print(
                f"{loteria:<20} | "
                f"{str(max_fecha) if max_fecha else 'None':<12} | "
                f"{estado}"
            )
        print("")
        conn2.close()
    except Exception:
        # La tabla informativa es opcional — si falla no afecta el exit code
        pass

    if total == 0:
        logger.info(
            "0 registros nuevos — la base de datos ya está al día "
            "o el sitio no publicó resultados nuevos. Esto es normal."
        )
    else:
        logger.info(f"Sincronización completada: {total} registro(s) nuevos.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
