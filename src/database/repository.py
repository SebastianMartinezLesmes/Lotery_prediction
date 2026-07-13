"""
Repositorio de datos de lotería.

Único módulo autorizado a ejecutar SQL. 
Todos los métodos retornan DataFrames con columnas:
    fecha (date), lottery (str), result (int), series (str)
"""
from __future__ import annotations

import pandas as pd
from datetime import date
from typing import List, Dict, Optional

from src.core.logger import LoggerManager
from src.database.connection import NeonConnection
from src.database.queries import (
    GET_LAST_DATE,
    GET_ALL_RESULTS,
    GET_RESULTS_BETWEEN,
    INSERT_RESULT,
    UPSERT_RESULT,
)

logger = LoggerManager.get_logger("lottery_repository", "log_loteria.log")

# Columnas canónicas que retorna siempre el repositorio
_COLUMNS = ["fecha", "lottery", "result", "series"]


def _rows_to_df(rows, col_names: List[str]) -> pd.DataFrame:
    """Convierte filas de cursor a DataFrame con tipos correctos."""
    if not rows:
        return pd.DataFrame(columns=_COLUMNS)
    df = pd.DataFrame(rows, columns=col_names)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    if "result" in df.columns:
        df["result"] = df["result"].astype(int)
    if "series" in df.columns:
        df["series"] = df["series"].astype(str)
    if "lottery" in df.columns:
        df["lottery"] = df["lottery"].astype(str)
    return df


class LotteriaRepository:
    """Acceso a datos de lotería en Neon PostgreSQL."""

    def __init__(self, connection: Optional[NeonConnection] = None):
        """
        Args:
            connection: Instancia de NeonConnection (se crea una nueva si no se pasa).
        """
        self._conn = connection or NeonConnection()

    # ------------------------------------------------------------------
    # Consultas de lectura
    # ------------------------------------------------------------------

    def get_last_date(self, loteria: str) -> Optional[date]:
        """
        Retorna la fecha más reciente registrada para la lotería indicada.

        Returns:
            date | None  (None si no hay registros)
        """
        conn = self._conn.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(GET_LAST_DATE, {"loteria": loteria})
                row = cur.fetchone()
                if row and row[0] is not None:
                    result = row[0]
                    # psycopg2 puede devolver date o datetime
                    if hasattr(result, "date"):
                        return result.date()
                    return result
                return None
        except Exception as e:
            logger.error(f"get_last_date({loteria}): {e}")
            raise

    def get_all_results(self, loteria: str) -> pd.DataFrame:
        """
        Retorna todos los resultados de la lotería ordenados por fecha.

        Returns:
            DataFrame con columnas [fecha, lottery, result, series]
        """
        conn = self._conn.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(GET_ALL_RESULTS, {"loteria": loteria})
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
            logger.info(f"get_all_results({loteria}): {len(rows)} registros")
            return _rows_to_df(rows, col_names)
        except Exception as e:
            logger.error(f"get_all_results({loteria}): {e}")
            raise

    def get_results_between(
        self,
        loteria: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> pd.DataFrame:
        """
        Retorna resultados en el rango [fecha_inicio, fecha_fin].

        Returns:
            DataFrame con columnas [fecha, lottery, result, series]
        """
        conn = self._conn.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    GET_RESULTS_BETWEEN,
                    {
                        "loteria": loteria,
                        "fecha_inicio": fecha_inicio,
                        "fecha_fin": fecha_fin,
                    },
                )
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
            logger.info(
                f"get_results_between({loteria}, {fecha_inicio}, {fecha_fin}): "
                f"{len(rows)} registros"
            )
            return _rows_to_df(rows, col_names)
        except Exception as e:
            logger.error(f"get_results_between({loteria}): {e}")
            raise

    # ------------------------------------------------------------------
    # Operaciones de escritura
    # ------------------------------------------------------------------

    def insert_results(self, records: List[Dict]) -> int:
        """
        Inserta una lista de registros.  Falla si ya existe el par (fecha, loteria_id).

        Args:
            records: Lista de dicts con claves fecha, loteria, result, series.

        Returns:
            Número de filas insertadas.
        """
        if not records:
            return 0
        conn = self._conn.get_connection()
        inserted = 0
        try:
            with conn.cursor() as cur:
                for rec in records:
                    cur.execute(INSERT_RESULT, rec)
                    inserted += cur.rowcount
            conn.commit()
            logger.info(f"insert_results: {inserted} registros insertados")
        except Exception as e:
            conn.rollback()
            logger.error(f"insert_results: {e}")
            raise
        return inserted

    def get_results_between_dates(
        self,
        loteria: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> pd.DataFrame:
        """Alias de get_results_between para compatibilidad con la especificación."""
        return self.get_results_between(loteria, fecha_inicio, fecha_fin)

    def update_result(self, fecha: date, loteria: str, result: int, series: str) -> bool:
        """
        Actualiza un resultado existente.

        Returns:
            True si se actualizó al menos una fila, False si no existía.
        """
        conn = self._conn.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    UPSERT_RESULT,
                    {"fecha": fecha, "loteria": loteria, "result": result, "series": series},
                )
                affected = cur.rowcount
            conn.commit()
            logger.info(f"update_result({fecha}, {loteria}): {affected} filas afectadas")
            return affected > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"update_result: {e}")
            raise

    # ------------------------------------------------------------------
    # Sincronización automática
    # ------------------------------------------------------------------

    def synchronize(self, loteria: str, scraper) -> dict:
        """
        Sincroniza Neon con los datos más recientes de SuperAstro.

        Flujo:
        1. Consulta MAX(fecha) para la lotería.
        2. Si ya está actualizado hasta ayer → retorna sin hacer nada.
        3. Calcula fecha_inicio = última_fecha + 1 día.
        4. Obtiene todos los resultados del scraper.
        5. Filtra el rango y hace upsert.
        6. Retorna métricas {insertados, actualizados, desde, hasta}.

        Args:
            loteria: Nombre de la lotería (ej: "ASTRO LUNA").
            scraper:  Instancia de SuperAstroScraper.

        Returns:
            dict con claves insertados, actualizados, desde, hasta.
        """
        from datetime import datetime, timedelta, date as date_type

        ayer = (datetime.now() - timedelta(days=1)).date()
        metricas: dict = {"insertados": 0, "actualizados": 0, "desde": None, "hasta": ayer}

        ultima_fecha = self.get_last_date(loteria)
        logger.info(f"synchronize({loteria}): última fecha en Neon = {ultima_fecha}")

        if ultima_fecha is not None and ultima_fecha >= ayer:
            logger.info(f"  {loteria}: ya actualizado hasta {ultima_fecha}. Nada que hacer.")
            metricas["desde"] = ultima_fecha
            return metricas

        fecha_inicio = (ultima_fecha + timedelta(days=1)) if ultima_fecha else None
        metricas["desde"] = fecha_inicio

        # Obtener todos los datos disponibles en la página
        todos = scraper.obtener_todos_resultados_pagina(loteria)

        nuevos = []
        for r in todos:
            try:
                fecha_r = datetime.strptime(r["fecha"], "%Y-%m-%d").date()
                if fecha_inicio is None or fecha_r >= fecha_inicio:
                    nuevos.append({
                        "fecha":   fecha_r,
                        "loteria": r["lottery"],
                        "result":  int(r["result"]),
                        "series":  r["series"],
                    })
            except (ValueError, KeyError):
                continue

        if not nuevos:
            logger.info(f"  {loteria}: no hay registros nuevos en el rango.")
            return metricas

        logger.info(f"  {loteria}: inserting/updating {len(nuevos)} registros...")
        n = self.upsert_results(nuevos)
        metricas["insertados"] = n
        logger.info(f"  {loteria}: {n} registros sincronizados.")
        return metricas

    def upsert_results(self, records: List[Dict]) -> int:
        """
        Inserta o actualiza registros (INSERT … ON CONFLICT DO UPDATE).

        Args:
            records: Lista de dicts con claves fecha, loteria, result, series.

        Returns:
            Número de filas afectadas.
        """
        if not records:
            return 0
        conn = self._conn.get_connection()
        affected = 0
        try:
            with conn.cursor() as cur:
                for rec in records:
                    cur.execute(UPSERT_RESULT, rec)
                    affected += cur.rowcount
            conn.commit()
            logger.info(f"upsert_results: {affected} registros upserted")
        except Exception as e:
            conn.rollback()
            logger.error(f"upsert_results: {e}")
            raise
        return affected
