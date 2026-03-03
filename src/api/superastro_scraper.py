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
    
    BASE_URL = "https://superastro.com.co/historico.php"
    
    # Mapeo de signos a abreviaciones de 3 letras
    SIGNOS_MAP = {
        'ARIES': 'ARI',
        'TAURO': 'TAU',
        'GEMINIS': 'GEM',
        'GÉMINIS': 'GEM',
        'CANCER': 'CAN',
        'CÁNCER': 'CAN',
        'LEO': 'LEO',
        'VIRGO': 'VIR',
        'LIBRA': 'LIB',
        'ESCORPIO': 'ESC',
        'ESCORPION': 'ESC',
        'SAGITARIO': 'SAG',
        'CAPRICORNIO': 'CAP',
        'ACUARIO': 'ACU',
        'PISCIS': 'PIS'
    }
    
    def __init__(self, delay_entre_requests: float = 1.0):
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
    
    def obtener_resultados_fecha(
        self,
        fecha: datetime,
        loteria: str = "ASTRO LUNA"
    ) -> Optional[Dict]:
        """
        Obtiene el resultado de una fecha específica.
        
        Args:
            fecha: Fecha del resultado
            loteria: "ASTRO SOL" o "ASTRO LUNA"
        
        Returns:
            Diccionario con el resultado o None
        """
        try:
            # La página muestra los últimos resultados por defecto
            # Necesitamos hacer scraping de la tabla
            
            logger.info(f"Obteniendo {loteria} para {fecha.strftime('%Y-%m-%d')}")
            
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar la tabla correcta según la lotería
            # La página tiene 2 tablas: una para astro sol y otra para astro luna
            tablas = soup.find_all('table')
            
            if len(tablas) < 2:
                logger.error(f"No se encontraron suficientes tablas en la página")
                return None
            
            # Determinar qué tabla usar
            # Tabla 0 = ASTRO SOL, Tabla 1 = ASTRO LUNA (generalmente)
            tabla_index = 1 if "LUNA" in loteria.upper() else 0
            tabla = tablas[tabla_index]
            
            # Extraer filas de la tabla
            filas = tabla.find_all('tr')
            
            fecha_buscar = fecha.strftime('%Y-%m-%d')
            
            for fila in filas[1:]:  # Saltar header
                celdas = fila.find_all('td')
                
                if len(celdas) >= 4:
                    fecha_celda = celdas[0].text.strip()
                    numero = celdas[1].text.strip()
                    signo = celdas[2].text.strip()
                    sorteo = celdas[3].text.strip() if len(celdas) > 3 else ""
                    
                    # Convertir fecha de formato dd-mm-yyyy a yyyy-mm-dd
                    try:
                        fecha_obj = datetime.strptime(fecha_celda, '%Y-%m-%d')
                        fecha_str = fecha_obj.strftime('%Y-%m-%d')
                    except:
                        # Intentar otros formatos
                        try:
                            fecha_obj = datetime.strptime(fecha_celda, '%d-%m-%Y')
                            fecha_str = fecha_obj.strftime('%Y-%m-%d')
                        except:
                            continue
                    
                    if fecha_str == fecha_buscar:
                        # Limpiar número (remover caracteres no numéricos)
                        numero_limpio = re.sub(r'\D', '', numero)
                        
                        if numero_limpio and len(numero_limpio) == 4:
                            resultado = {
                                'fecha': fecha_str,
                                'lottery': loteria,
                                'result': int(numero_limpio),
                                'series': self.normalizar_signo(signo)
                            }
                            
                            logger.info(f"  ✓ Encontrado: {numero_limpio} - {signo}")
                            return resultado
            
            logger.warning(f"  ✗ No se encontró resultado para {fecha_buscar}")
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo resultado: {e}")
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
        
        Args:
            loteria: "ASTRO SOL" o "ASTRO LUNA"
            excel_path: Ruta al archivo Excel
            hasta_fecha: Fecha límite (por defecto: ayer)
        
        Returns:
            Lista de resultados nuevos obtenidos
        """
        # Obtener última fecha
        desde_fecha = self.obtener_ultima_fecha(excel_path, loteria)
        
        # Fecha límite: ayer
        if hasta_fecha is None:
            hasta_fecha = datetime.now() - timedelta(days=1)
        
        # Ajustar desde_fecha para no duplicar
        desde_fecha = desde_fecha + timedelta(days=1)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"ACTUALIZANDO: {loteria}")
        logger.info(f"Desde: {desde_fecha.strftime('%Y-%m-%d')}")
        logger.info(f"Hasta: {hasta_fecha.strftime('%Y-%m-%d')}")
        logger.info('='*70)
        
        # Obtener resultados día por día
        resultados_nuevos = []
        fecha_actual = desde_fecha
        
        while fecha_actual <= hasta_fecha:
            resultado = self.obtener_resultados_fecha(fecha_actual, loteria)
            
            if resultado:
                resultados_nuevos.append(resultado)
            
            fecha_actual += timedelta(days=1)
            
            # Pausa entre requests
            if fecha_actual <= hasta_fecha:
                time.sleep(self.delay)
        
        logger.info(f"\n✓ Obtenidos {len(resultados_nuevos)} resultados nuevos para {loteria}")
        
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
