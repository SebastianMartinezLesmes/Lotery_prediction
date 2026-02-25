"""
Cliente HTTP mejorado para consumir la API de resultados de lotería.
"""
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

from src.core.config import settings
from src.core.exceptions import APIError
from src.core.logger import get_api_logger
from src.models.schemas import APIResponse

logger = get_api_logger()


class LotteryAPIClient:
    """Cliente para interactuar con la API de resultados de lotería."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Inicializa el cliente de API.
        
        Args:
            base_url: URL base de la API (usa settings.API_URL por defecto)
            timeout: Timeout en segundos para las peticiones
            max_retries: Número máximo de reintentos
        """
        self.base_url = base_url or settings.API_URL
        self.timeout = timeout
        self.session = self._create_session(max_retries)
        logger.info(f"Cliente API inicializado: {self.base_url}")
    
    def _create_session(self, max_retries: int) -> requests.Session:
        """
        Crea una sesión HTTP con reintentos automáticos.
        
        Args:
            max_retries: Número máximo de reintentos
        
        Returns:
            Sesión configurada
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def get_results_by_date(self, fecha: date) -> Dict[str, Any]:
        """
        Obtiene resultados de lotería para una fecha específica.
        
        Args:
            fecha: Fecha para consultar
        
        Returns:
            Diccionario con los resultados
        
        Raises:
            APIError: Si hay un error en la petición
        """
        fecha_str = fecha.strftime("%Y-%m-%d")
        url = f"{self.base_url}{fecha_str}"
        
        try:
            logger.debug(f"Consultando API: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Respuesta recibida para {fecha_str}")
            return data
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout al consultar {url}"
            logger.error(error_msg)
            raise APIError(error_msg)
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"Error HTTP {e.response.status_code}: {url}"
            logger.error(error_msg)
            raise APIError(error_msg)
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg)
        
        except ValueError as e:
            error_msg = f"Error al parsear JSON: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg)
    
    def filter_lottery_results(
        self,
        results: List[Dict[str, Any]],
        lottery_name: str
    ) -> List[Dict[str, Any]]:
        """
        Filtra resultados por nombre de lotería.
        
        Args:
            results: Lista de resultados
            lottery_name: Nombre de la lotería a filtrar
        
        Returns:
            Lista de resultados filtrados
        """
        filtered = [
            r for r in results
            if lottery_name.upper() in r.get("lottery", "").upper()
        ]
        logger.debug(f"Filtrados {len(filtered)} resultados para {lottery_name}")
        return filtered
    
    def remove_duplicates(
        self,
        results: List[Dict[str, Any]],
        keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Elimina resultados duplicados basándose en claves específicas.
        
        Args:
            results: Lista de resultados
            keys: Claves para identificar duplicados (usa settings.CLAVES_UNICAS por defecto)
        
        Returns:
            Lista sin duplicados
        """
        if keys is None:
            keys = settings.CLAVES_UNICAS
        
        seen = set()
        unique_results = []
        
        for item in results:
            # Crear tupla con los valores de las claves
            identity = tuple(item.get(key) for key in keys)
            
            if identity not in seen:
                seen.add(identity)
                unique_results.append(item)
        
        duplicates_removed = len(results) - len(unique_results)
        if duplicates_removed > 0:
            logger.info(f"Eliminados {duplicates_removed} duplicados")
        
        return unique_results
    
    def get_historical_results(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        lottery_filter: Optional[str] = None,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Obtiene resultados históricos en un rango de fechas.
        
        Args:
            fecha_inicio: Fecha de inicio (usa settings.FECHA_DEFECTO por defecto)
            fecha_fin: Fecha de fin (usa hoy por defecto)
            lottery_filter: Filtrar por nombre de lotería (opcional)
            show_progress: Mostrar barra de progreso
        
        Returns:
            Lista de resultados históricos
        
        Raises:
            APIError: Si hay errores en las peticiones
        """
        if fecha_inicio is None:
            fecha_inicio = datetime.strptime(
                settings.FECHA_DEFECTO,
                "%Y-%m-%d"
            ).date()
        
        if fecha_fin is None:
            fecha_fin = date.today()
        
        if fecha_inicio > fecha_fin:
            raise APIError("La fecha de inicio no puede ser posterior a la fecha de fin")
        
        dias_totales = (fecha_fin - fecha_inicio).days + 1
        logger.info(f"Obteniendo resultados desde {fecha_inicio} hasta {fecha_fin} ({dias_totales} días)")
        
        all_results = []
        errors = []
        
        iterator = range(dias_totales)
        if show_progress:
            iterator = tqdm(
                iterator,
                desc=f"Obteniendo {lottery_filter or 'resultados'}",
                unit="día"
            )
        
        for i in iterator:
            fecha_actual = fecha_inicio + timedelta(days=i)
            
            try:
                data = self.get_results_by_date(fecha_actual)
                results_dia = data.get("data", [])
                
                # Filtrar por lotería si se especifica
                if lottery_filter:
                    results_dia = self.filter_lottery_results(results_dia, lottery_filter)
                
                # Eliminar duplicados
                results_dia = self.remove_duplicates(results_dia)
                
                if results_dia:
                    all_results.append({
                        "fecha": fecha_actual.strftime("%Y-%m-%d"),
                        "resultados": results_dia
                    })
                    logger.debug(f"✅ {len(results_dia)} resultados para {fecha_actual}")
                else:
                    logger.debug(f"❌ Sin resultados para {fecha_actual}")
            
            except APIError as e:
                errors.append(f"{fecha_actual}: {str(e)}")
                logger.warning(f"Error obteniendo datos para {fecha_actual}: {e}")
                continue
        
        if errors:
            logger.warning(f"Se encontraron {len(errors)} errores durante la obtención de datos")
        
        logger.info(f"Total de días con resultados: {len(all_results)}")
        return all_results
    
    def close(self) -> None:
        """Cierra la sesión HTTP."""
        self.session.close()
        logger.info("Sesión API cerrada")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
