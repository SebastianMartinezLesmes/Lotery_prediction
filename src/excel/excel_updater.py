"""
Sistema inteligente de actualización incremental de datos de lotería.

Este módulo implementa dos estrategias:
1. Si no existe el Excel: Consulta desde FECHA_DEFECTO hasta hoy
2. Si existe el Excel: Consulta desde la última fecha guardada hasta hoy
"""
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from openpyxl import load_workbook

from src.core.config import settings
from src.core.logger import get_logger
from src.core.exceptions import APIError
from src.api.superastro_scraper import SuperAstroScraper

logger = get_logger(__name__)

# Fecha de inicio por defecto si no existe el Excel
FECHA_DEFECTO = date(2020, 1, 1)


def obtener_ultima_fecha_excel(ruta_excel: Path) -> Optional[date]:
    """
    Lee el archivo Excel y retorna la última fecha registrada.

    Args:
        ruta_excel: Ruta al archivo Excel

    Returns:
        Última fecha encontrada o None si no hay datos
    """
    try:
        df = pd.read_excel(ruta_excel)
        if df.empty or "fecha" not in df.columns:
            return None
        df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
        return df["fecha"].max().date()
    except Exception as e:
        logger.warning(f"No se pudo leer el Excel existente: {e}")
        return None


def actualizar_excel_incremental(
    loterias: Optional[List[str]] = None,
    ruta_excel: Optional[Path] = None,
) -> int:
    """
    Actualiza el Excel de forma incremental.

    Estrategia:
    - Si el Excel no existe: consulta desde FECHA_DEFECTO hasta hoy.
    - Si el Excel existe: consulta desde la última fecha guardada hasta hoy.

    Args:
        loterias: Lista de loterías a consultar. Por defecto usa settings.LOTTERIES.
        ruta_excel: Ruta al archivo Excel. Por defecto usa settings.get_excel_path().

    Returns:
        Número de filas nuevas añadidas.
    """
    if loterias is None:
        loterias = list(settings.LOTTERIES)
    if ruta_excel is None:
        ruta_excel = settings.get_excel_path()

    hoy = date.today()
    scraper = SuperAstroScraper()
    nuevas_filas = 0

    for loteria in loterias:
        logger.info(f"Actualizando datos para: {loteria}")

        if ruta_excel.exists():
            ultima_fecha = obtener_ultima_fecha_excel(ruta_excel)
            fecha_inicio = (ultima_fecha + timedelta(days=1)) if ultima_fecha else FECHA_DEFECTO
        else:
            fecha_inicio = FECHA_DEFECTO

        if fecha_inicio > hoy:
            logger.info(f"{loteria}: datos ya están al día (última fecha: {fecha_inicio - timedelta(days=1)})")
            continue

        logger.info(f"{loteria}: consultando desde {fecha_inicio} hasta {hoy}")

        try:
            resultados: List[Dict[str, Any]] = scraper.obtener_resultados(
                loteria=loteria,
                fecha_inicio=datetime.combine(fecha_inicio, datetime.min.time()),
                fecha_fin=datetime.combine(hoy, datetime.min.time()),
            )

            if not resultados:
                logger.info(f"{loteria}: sin resultados nuevos")
                continue

            df_nuevo = pd.DataFrame(resultados)

            if ruta_excel.exists():
                df_existente = pd.read_excel(ruta_excel)
                df_total = pd.concat([df_existente, df_nuevo], ignore_index=True)
                df_total = df_total.drop_duplicates(subset=settings.CLAVES_UNICAS)
            else:
                settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
                df_total = df_nuevo

            df_total.to_excel(ruta_excel, index=False)
            nuevas_filas += len(df_nuevo)
            logger.info(f"{loteria}: {len(df_nuevo)} filas añadidas")

        except APIError as e:
            logger.error(f"{loteria}: error de API — {e}")
        except Exception as e:
            logger.error(f"{loteria}: error inesperado — {e}")

    return nuevas_filas
