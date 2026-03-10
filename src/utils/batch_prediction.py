"""
Módulo para predicciones por lotes (batch predictions).
Permite predecir múltiples fechas de una vez de manera eficiente.
"""
import os
import json
import joblib
import argparse
import pandas as pd

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from src.core.logger import get_logger
from src.core.config import settings
from src.excel.read_excel import obtener_loterias_disponibles

logger = get_logger(__name__)

# Mapeo de códigos a signos zodiacales
ZODIACO = [
    "ARI", "TAU", "GEM", "CAN",
    "LEO", "VIR", "LIB", "ESC",
    "SAG", "CAP", "ACU", "PIS"
]

def obtener_zodiaco(codigo):
    """Convierte código numérico a signo zodiacal (abreviación de 3 letras)."""
    try:
        return ZODIACO[int(codigo)]
    except:
        return str(codigo)


class BatchPredictor:
    """Predictor por lotes para múltiples fechas."""
    
    def __init__(self, loteria: str):
        """
        Inicializa el predictor por lotes.
        
        Args:
            loteria: Nombre de la lotería
        """
        self.loteria = loteria
        self.nombre_archivo = loteria.replace(" ", "_").lower()
        self.modelo_result_path = settings.MODELS_DIR / f"modelo_result_{self.nombre_archivo}.pkl"
        self.modelo_series_path = settings.MODELS_DIR / f"modelo_series_{self.nombre_archivo}.pkl"
        
        # Cargar modelos
        self._cargar_modelos()
    
    def _cargar_modelos(self) -> None:
        """Carga los modelos entrenados."""
        if not self.modelo_result_path.exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {self.modelo_result_path}\n"
                f"Ejecuta primero: python main.py --train --lottery {self.loteria}"
            )
        
        if not self.modelo_series_path.exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {self.modelo_series_path}\n"
                f"Ejecuta primero: python main.py --train --lottery {self.loteria}"
            )
        
        logger.info(f"Cargando modelos para {self.loteria}...")
        self.modelo_result = joblib.load(self.modelo_result_path)
        self.modelo_series = joblib.load(self.modelo_series_path)
        logger.info("Modelos cargados exitosamente")
    
    def predecir_fecha(self, fecha: datetime) -> Dict[str, any]:
        """
        Predice para una fecha específica.
        
        Args:
            fecha: Fecha para la predicción
            
        Returns:
            Diccionario con la predicción
        """
        X = pd.DataFrame([{
            "dia": fecha.day,
            "mes": fecha.month,
            "anio": fecha.year,
            "dia_semana": fecha.weekday()
        }])
        
        numero = self.modelo_result.predict(X)[0]
        simbolo_codificado = self.modelo_series.predict(X)[0]
        simbolo = obtener_zodiaco(simbolo_codificado)
        
        return {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "dia_semana": fecha.strftime("%A"),
            "numero": str(numero).zfill(4),
            "simbolo": simbolo
        }
    
    def predecir_rango(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime
    ) -> List[Dict[str, any]]:
        """
        Predice para un rango de fechas.
        
        Args:
            fecha_inicio: Fecha inicial
            fecha_fin: Fecha final
            
        Returns:
            Lista de predicciones
        """
        predicciones = []
        fecha_actual = fecha_inicio
        
        while fecha_actual <= fecha_fin:
            prediccion = self.predecir_fecha(fecha_actual)
            predicciones.append(prediccion)
            fecha_actual += timedelta(days=1)
        
        return predicciones
    
    def predecir_proximos_dias(self, dias: int = 7) -> List[Dict[str, any]]:
        """
        Predice para los próximos N días.
        
        Args:
            dias: Número de días a predecir
            
        Returns:
            Lista de predicciones
        """
        hoy = datetime.today()
        fecha_fin = hoy + timedelta(days=dias - 1)
        return self.predecir_rango(hoy, fecha_fin)
    
    def predecir_fechas_especificas(
        self,
        fechas: List[datetime]
    ) -> List[Dict[str, any]]:
        """
        Predice para fechas específicas.
        
        Args:
            fechas: Lista de fechas
            
        Returns:
            Lista de predicciones
        """
        return [self.predecir_fecha(fecha) for fecha in fechas]


def predecir_batch_todas_loterias(
    dias: int = 7,
    loterias: Optional[List[str]] = None
) -> Dict[str, List[Dict[str, any]]]:
    """
    Predice para todas las loterías disponibles.
    
    Args:
        dias: Número de días a predecir
        loterias: Lista de loterías específicas (opcional)
        
    Returns:
        Diccionario con predicciones por lotería
    """
    
    if loterias is None:
        loterias = obtener_loterias_disponibles()
    
    resultados = {}
    
    for loteria in loterias:
        try:
            logger.info(f"Generando predicciones batch para {loteria}...")
            predictor = BatchPredictor(loteria)
            predicciones = predictor.predecir_proximos_dias(dias)
            resultados[loteria] = predicciones
            logger.info(f"Completado: {len(predicciones)} predicciones para {loteria}")
        except Exception as e:
            logger.error(f"Error en {loteria}: {e}")
            resultados[loteria] = {"error": str(e)}
    
    return resultados


def guardar_predicciones_batch(
    predicciones: Dict[str, List[Dict[str, any]]],
    archivo: Optional[Path] = None
) -> None:
    """
    Guarda las predicciones batch en un archivo JSON.
    
    Args:
        predicciones: Diccionario con predicciones
        archivo: Ruta del archivo (opcional)
    """
    if archivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo = settings.DATA_DIR / f"batch_predictions_{timestamp}.json"
    
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(predicciones, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Predicciones guardadas en: {archivo}")


def mostrar_predicciones_batch(
    predicciones: Dict[str, List[Dict[str, any]]]
) -> None:
    """
    Muestra las predicciones batch en consola de forma legible.
    
    Args:
        predicciones: Diccionario con predicciones
    """
    print("\n" + "="*70)
    print("PREDICCIONES BATCH - MÚLTIPLES FECHAS")
    print("="*70)
    
    for loteria, preds in predicciones.items():
        print(f"\n>> {loteria.upper()}")
        print("-" * 70)
        
        if isinstance(preds, dict) and "error" in preds:
            print(f"   ERROR: {preds['error']}")
            continue
        
        for pred in preds:
            print(f"   {pred['fecha']} ({pred['dia_semana'][:3]}) | "
                  f"Número: {pred['numero']} | Símbolo: {pred['simbolo']}")
    
    print("\n" + "="*70)


def main():
    """Función principal para pruebas."""
    
    parser = argparse.ArgumentParser(description="Predicciones por lotes")
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Número de días a predecir (default: 7)'
    )
    parser.add_argument(
        '--lottery',
        type=str,
        help='Lotería específica (opcional)'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Guardar resultados en archivo JSON'
    )
    
    args = parser.parse_args()
    
    # Obtener loterías
    loterias = [args.lottery] if args.lottery else None
    
    # Generar predicciones
    print(f"\nGenerando predicciones para los próximos {args.days} días...")
    predicciones = predecir_batch_todas_loterias(dias=args.days, loterias=loterias)
    
    # Mostrar resultados
    mostrar_predicciones_batch(predicciones)
    
    # Guardar si se solicita
    if args.save:
        guardar_predicciones_batch(predicciones)
        print(f"\n>> Predicciones guardadas en: data/batch_predictions_*.json")


if __name__ == "__main__":
    main()
