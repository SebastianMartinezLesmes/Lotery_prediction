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
from src.api.client import LotteryAPIClient

logger = get_logger(_