"""
Scraper para SuperAstro - Fuente oficial de resultados.

URL: https://superastro.com.co/historico.php

Este scraper obtiene datos directamente del sitio oficial,
lo que lo hace mucho más confiable que buscar en Google.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import re

from src.core.logger import LoggerManager
from src.core.config import settings

logger = LoggerManager.get_logger("superastro_scraper", "scraper.log")


class SuperAstroScraper:
    """
    Scraper para obtener resultados de SuperAstro desde el sitio oficial.
    """
    
    BASE_URL = settings.API_URL
    
    # Mapeo de signos a abreviaciones de 3 letras
    SIGNOS_MAP = settings.zodiaco
    
    def __init__(self, delay_entre_requests: float = settings.SCRAPER_DELAY_DEFAULT):
        """
        Inicializa el scraper.
        
        Args:
            delay_entre_requests: Segundos de espera entre requests
        """
        self.delay = delay_entre_requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def normalizar_signo(self, signo: str) -> str:
        """
        Normaliza el nombre del signo zodiacal.
        
        Args:
            signo: Nombre del signo (puede ser abreviado o con acentos)
        
        Returns:
            Nombre normalizado del signo
        """
        signo_upper = signo.upper().strip()
        return self.SIGNOS_MAP.get(signo_upper, signo_upper)
    
    def _parsear_tabla(self, soup: BeautifulSoup, loteria: str) -> List[Dict]:
        """
        Extrae todos los resultados disponibles de la tabla HTML en una sola llamada.

        Returns:
            Lista de dicts con todos los resultados encontrados en la página.
        """
        tablas = soup.find_all('table')
        if len(tablas) < 2:
            logger.error("No se encontraron suficientes tablas en la página")
            return []

        tabla_index = 1 if "LUNA" in loteria.upper() else 0
        tabla = tablas[tabla_index]
        filas = tabla.find_all('tr')

        resultados = []
        for fila in filas[1:]:
            celdas = fila.find_all('td')
            if len(celdas) < 3:
                continue

            fecha_celda = celdas[0].text.strip()
            numero      = celdas[1].text.strip()
            signo       = celdas[2].text.strip()

            # Parsear fecha (varios formatos posibles)
            fecha_obj = None
            for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                try:
                    fecha_obj = datetime.strptime(fecha_celda, fmt)
                    break
                except ValueError:
                    continue
            if fecha_obj is None:
                continue

            numero_limpio = re.sub(r'\D', '', numero)
            if not numero_limpio or len(numero_limpio) != 4:
                continue

            resultados.append({
                'fecha':   fecha_obj.strftime('%Y-%m-%d'),
                'lottery': loteria,
                'result':  int(numero_limpio),
                'series':  self.normalizar_signo(signo)
            })

        return resultados

    def obtener_todos_resultados_pagina(self, loteria: str) -> List[Dict]:
        """
        Obtiene TODOS los resultados disponibles en la página en un solo request.
        Mucho más eficiente que consultar fecha por fecha.
        """
        try:
            logger.info(f"Obteniendo todos los resultados de {loteria} (1 request)...")
            response = self.session.get(self.BASE_URL, timeout=settings.SCRAPER_REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            resultados = self._parsear_tabla(soup, loteria)
            logger.info(f"  ✓ {len(resultados)} resultados encontrados en la página")
            return resultados
        except Exception as e:
            logger.error(f"Error obteniendo resultados: {e}")
            return []

    def obtener_resultados_fecha(
        self,
        fecha: datetime,
        loteria: str = "ASTRO LUNA"
    ) -> Optional[Dict]:
        """Obtiene el resultado de una fecha específica (usa caché de página)."""
        todos = self.obtener_todos_resultados_pagina(loteria)
        fecha_buscar = fecha.strftime('%Y-%m-%d')
        for r in todos:
            if r['fecha'] == fecha_buscar:
                return r
        logger.warning(f"  ✗ No se encontró resultado para {fecha_buscar}")
        return None
    
    def obtener_ultima_fecha(self, excel_path: str, loteria: str) -> datetime:
        """
        Obtiene la última fecha registrada para una lotería.
        
        Args:
            excel_path: Ruta al archivo Excel
            loteria: Nombre de la lotería
        
        Returns:
            Última fecha registrada o fecha por defecto
        """
        try:
            df = pd.read_excel(excel_path)
            df_loteria = df[df['lottery'].str.upper() == loteria.upper()]
            
            if len(df_loteria) > 0:
                df_loteria['fecha'] = pd.to_datetime(df_loteria['fecha'])
                ultima_fecha = df_loteria['fecha'].max()
                logger.info(f"Última fecha en Excel para {loteria}: {ultima_fecha.strftime('%Y-%m-%d')}")
                return ultima_fecha
            else:
                # Si no hay datos, empezar desde hace 30 días
                fecha_inicio = datetime.now() - timedelta(days=30)
                logger.info(f"No hay datos previos para {loteria}, iniciando desde: {fecha_inicio.strftime('%Y-%m-%d')}")
                return fecha_inicio
        except FileNotFoundError:
            # Si el archivo no existe, empezar desde hace 30 días
            fecha_inicio = datetime.now() - timedelta(days=30)
            logger.info(f"Archivo Excel no encontrado, iniciando desde: {fecha_inicio.strftime('%Y-%m-%d')}")
            return fecha_inicio
        except Exception as e:
            logger.error(f"Error obteniendo última fecha: {e}")
            # En caso de error, empezar desde hace 7 días
            return datetime.now() - timedelta(days=7)
    
    def actualizar_loteria(
        self,
        loteria: str,
        excel_path: str,
        hasta_fecha: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Actualiza los resultados de una lotería desde la última fecha hasta ayer.
        Obtiene todos los datos en UN solo request y filtra por rango de fechas.
        """
        desde_fecha = self.obtener_ultima_fecha(excel_path, loteria) + timedelta(days=1)

        if hasta_fecha is None:
            hasta_fecha = datetime.now() - timedelta(days=1)

        logger.info(f"\n{'='*70}")
        logger.info(f"ACTUALIZANDO: {loteria}")
        logger.info(f"Desde: {desde_fecha.strftime('%Y-%m-%d')}")
        logger.info(f"Hasta: {hasta_fecha.strftime('%Y-%m-%d')}")
        logger.info('='*70)

        if desde_fecha > hasta_fecha:
            logger.info("Los datos ya están actualizados.")
            return []

        # Un solo request para todos los datos disponibles
        todos = self.obtener_todos_resultados_pagina(loteria)

        # Filtrar solo el rango que necesitamos
        resultados_nuevos = []
        for r in todos:
            try:
                fecha_r = datetime.strptime(r['fecha'], '%Y-%m-%d')
                if desde_fecha <= fecha_r <= hasta_fecha:
                    resultados_nuevos.append(r)
            except ValueError:
                continue

        logger.info(f"✓ {len(resultados_nuevos)} resultados nuevos para {loteria}")
        return resultados_nuevos
    
    def actualizar_todas_loterias(
        self,
        excel_path: str,
        loterias: Optional[List[str]] = None,
        filtro: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Actualiza las loterías especificadas.
        
        Args:
            excel_path: Ruta al archivo Excel
            loterias: Lista de loterías a actualizar (opcional)
            filtro: Filtro para loterías (opcional)
        
        Returns:
            DataFrame con todos los resultados nuevos
        """
        # Loterías disponibles en SuperAstro
        loterias_disponibles = ["ASTRO SOL", "ASTRO LUNA"]
        
        if loterias is None:
            if filtro:
                # Filtrar loterías
                filtro_upper = filtro.upper().strip()
                loterias = [l for l in loterias_disponibles if filtro_upper in l]
                
                if not loterias:
                    logger.warning(f"No se encontraron loterías que coincidan con: {filtro}")
                    logger.info(f"Loterías disponibles: {loterias_disponibles}")
                    return pd.DataFrame()
            else:
                loterias = loterias_disponibles
        
        logger.info(f"\n{'='*70}")
        logger.info(f"ACTUALIZACIÓN DESDE SUPERASTRO")
        logger.info(f"{'='*70}")
        if filtro:
            logger.info(f"Filtro aplicado: '{filtro}'")
        logger.info(f"Loterías a actualizar: {loterias}")
        logger.info('='*70)
        
        todos_resultados = []
        
        for loteria in loterias:
            try:
                resultados = self.actualizar_loteria(loteria, excel_path)
                todos_resultados.extend(resultados)
            except Exception as e:
                logger.error(f"Error actualizando {loteria}: {e}")
                continue
        
        # Convertir a DataFrame
        if todos_resultados:
            df_nuevos = pd.DataFrame(todos_resultados)
            logger.info(f"\n{'='*70}")
            logger.info(f"RESUMEN DE ACTUALIZACIÓN")
            logger.info(f"{'='*70}")
            logger.info(f"Total de resultados nuevos: {len(df_nuevos)}")
            logger.info(f"Por lotería:")
            for loteria in df_nuevos['lottery'].unique():
                count = len(df_nuevos[df_nuevos['lottery'] == loteria])
                logger.info(f"  - {loteria}: {count} resultados")
            logger.info('='*70)
            
            return df_nuevos
        else:
            logger.info("\nNo se obtuvieron resultados nuevos")
            return pd.DataFrame()
    
    def guardar_resultados(self, df_nuevos: pd.DataFrame, excel_path: str):
        """
        Guarda los resultados nuevos en el archivo Excel.
        
        Args:
            df_nuevos: DataFrame con resultados nuevos
            excel_path: Ruta al archivo Excel
        """
        if df_nuevos.empty:
            logger.info("No hay resultados nuevos para guardar")
            return
        
        try:
            # Leer datos existentes
            try:
                df_existente = pd.read_excel(excel_path)
            except FileNotFoundError:
                df_existente = pd.DataFrame()
            
            # Combinar datos
            if not df_existente.empty:
                df_combinado = pd.concat([df_existente, df_nuevos], ignore_index=True)
                
                # Eliminar duplicados
                df_combinado = df_combinado.drop_duplicates(
                    subset=['fecha', 'lottery'],
                    keep='last'
                )
                
                # Ordenar por fecha
                df_combinado['fecha'] = pd.to_datetime(df_combinado['fecha'])
                df_combinado = df_combinado.sort_values('fecha')
            else:
                df_combinado = df_nuevos
            
            # Guardar
            df_combinado.to_excel(excel_path, index=False)
            logger.info(f"\n✓ Resultados guardados en: {excel_path}")
            logger.info(f"  Total de registros: {len(df_combinado)}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")
            raise


def main():
    """Función principal para actualización automática."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SuperAstro Scraper - Actualización desde sitio oficial"
    )
    
    parser.add_argument(
        '--filtro',
        type=str,
        help='Filtrar loterías (ej: astro, luna, sol)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Segundos entre requests (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Configuración
    excel_path = settings.get_excel_path()
    
    # Crear scraper
    scraper = SuperAstroScraper(delay_entre_requests=args.delay)
    
    # Actualizar loterías
    df_nuevos = scraper.actualizar_todas_loterias(
        str(excel_path),
        filtro=args.filtro
    )
    
    # Guardar resultados
    if not df_nuevos.empty:
        scraper.guardar_resultados(df_nuevos, str(excel_path))
        print(f"\n✓ Actualización completada: {len(df_nuevos)} resultados nuevos")
    else:
        print("\n✓ No hay resultados nuevos. Los datos están actualizados.")


if __name__ == "__main__":
    main()
