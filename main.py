"""
Punto de entrada alternativo con CLI mejorado.
Permite ejecutar componentes individuales o el pipeline completo.
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd

from typing import Optional
from src.core.config import settings
from src.core.logger import get_main_logger
from src.api.superastro_scraper import SuperAstroScraper
from src.utils.drop_cache import main as drop_cache_main
from src.utils.prediction import main as prediction_main
from src.utils.training import entrenar_modelos_por_loteria
from src.features.feature_engineering import generar_features

logger = get_main_logger()

def ejecutar_limpieza() -> bool:
    """4. Limpia archivos de caché de Python."""
    try:
        logger.info("="*70)
        logger.info("4. LIMPIEZA DE CACHE")
        logger.info("="*70)
        
        print(f"\n{'='*70}")
        print("4. LIMPIEZA DE CACHE")
        print('='*70)
        
        drop_cache_main()
        
        print("\n✅ Limpieza completada")
        return True
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        print(f"\n❌ Error: {e}")
        return False


def ejecutar_actualizacion(filtro_loteria: Optional[str] = None) -> bool:
    """
    1. Actualizar datos desde SuperAstro.
    
    Args:
        filtro_loteria: Filtro para loterías (ej: "astro", "luna", "sol")
    """
    try:
        logger.info("="*70)
        logger.info("1. ACTUALIZACIÓN DE DATOS DESDE SUPERASTRO")
        logger.info("="*70)
        
        excel_path = settings.get_excel_path()
        
        print(f"\n{'='*70}")
        print("1. ACTUALIZACIÓN DE DATOS")
        print('='*70)
        print(f"Fuente: SuperAstro (sitio oficial)")
        print(f"Archivo: {excel_path}")
        if filtro_loteria:
            print(f"Filtro: {filtro_loteria}")
        print('='*70)
        
        # Crear scraper
        scraper = SuperAstroScraper(delay_entre_requests = 1.0)
        
        # Actualizar loterías
        df_nuevos = scraper.actualizar_todas_loterias(
            str(excel_path),
            filtro=filtro_loteria
        )
        
        # Guardar resultados
        if not df_nuevos.empty:
            scraper.guardar_resultados(df_nuevos, str(excel_path))
            print(f"\n✅ Actualización completada: {len(df_nuevos)} resultados nuevos")
        else:
            print("\n✅ No hay resultados nuevos. Los datos están actualizados.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en actualización: {e}")
        print(f"\n❌ Error: {e}")
        return False


def ejecutar_entrenamiento(loteria: Optional[str] = None) -> bool:
    """
    2. Entrena modelos de ML con features avanzadas.
    
    Args:
        loteria: Nombre específico de lotería (opcional)
    """
    try:
        logger.info("="*70)
        logger.info("2. ENTRENAMIENTO DE MODELOS")
        logger.info("="*70)
        
        print(f"\n{'='*70}")
        print("2. ENTRENAMIENTO DE MODELOS CON FEATURES AVANZADAS + Genetica IA")
        print('='*70)
        
        # Ruta al archivo Excel
        ruta_excel = settings.get_excel_path()
        
        if not os.path.exists(ruta_excel):
            print(f"❌ Archivo no encontrado: {ruta_excel}")
            print("   Ejecuta primero: python main.py --actualizar")
            return False
        
        print(f"Leyendo datos desde: {ruta_excel}")
        
        # Leer datos
        df = pd.read_excel(ruta_excel)
        
        # Validar columnas
        columnas_necesarias = {"fecha", "lottery", "result", "series"}
        if not columnas_necesarias.issubset(df.columns):
            print(f"❌ Faltan columnas necesarias: {columnas_necesarias - set(df.columns)}")
            return False
        
        # Preprocesar
        df = df.dropna(subset=["fecha", "lottery", "result", "series"])
        df["result"] = df["result"].astype(int)
        df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
        df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
        
        # Obtener loterías
        if loteria:
            # Filtrar loterías que contengan el texto especificado
            loteria_lower = loteria.lower()
            loterias_disponibles = df["lottery"].unique()
            loterias = [l for l in loterias_disponibles if loteria_lower in l.lower()]
            
            if not loterias:
                print(f"❌ No se encontraron loterías que coincidan con: {loteria}")
                print(f"   Loterías disponibles: {list(loterias_disponibles)}")
                return False
        else:
            loterias = df["lottery"].unique()
        
        print(f"\nLoterías a entrenar: {list(loterias)}")
        print(f"Features: Avanzadas (temporales + lag + rolling + tendencias)")
        print('='*70)
        
        # Entrenar cada lotería
        for nombre_loteria in loterias:
            print(f"\n{'='*70}")
            print(f"Entrenando modelos para: {nombre_loteria.upper()}")
            print('='*70)
            
            df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()].copy()
            
            if len(df_loteria) < 50:
                print(f"❌ Datos insuficientes para {nombre_loteria}: {len(df_loteria)} registros")
                print("   Se necesitan al menos 50 registros")
                continue
            
            # Ordenar por fecha
            df_loteria = df_loteria.sort_values("fecha").reset_index(drop=True)
            
            # ============================================================
            # FEATURES AVANZADAS PARA MAYOR PRECISIÓN
            # ============================================================
            X_df = generar_features(df_loteria)

            # limpiar posibles NaN generados por lag/rolling
            X_df = X_df.replace([np.inf, -np.inf], np.nan).dropna()

            # alinear dataframe con features
            df_loteria = df_loteria.tail(len(X_df))

            # 5. Features de tendencia
            df_loteria["tendencia_7"] = (
                df_loteria["result"].rolling(window=7, min_periods=1).apply(
                    lambda x: 1 if len(x) > 1 and x.iloc[-1] > x.iloc[0] else 0
                )
            )
            
            # 6. Features de frecuencia
            df_loteria["result_freq_mean"] = df_loteria["result"].rolling(window=30, min_periods=1).mean()
            df_loteria["result_freq_std"] = df_loteria["result"].rolling(window=30, min_periods=1).std()
                        
            # alinear dataframe con features generadas
            df_loteria = df_loteria.tail(len(X_df))
            X_l = X_df.values
            y_r = df_loteria["result"].values
            y_s = df_loteria["series"].values
            cols = list(X_df.columns)
            
            print(f"\nDatos preparados:")
            print(f"  Registros: {X_l.shape[0]}")
            print(f"  Features: {X_l.shape[1]}")

            cols = list(X_df.columns)
            print(f"  Features usadas: {', '.join(cols[:5])}... (+{len(cols)-5} más)")
            
            entrenar_modelos_por_loteria(
                X=X_l,
                y_result=y_r,
                y_series=y_s,
                nombre_loteria=nombre_loteria,
                min_acc=settings.TRAINING_CONFIGURE["min_accuracy"],
                max_iter=settings.TRAINING_CONFIGURE["max_iterations"],
                verbose=True
            )
        
        print(f"\n{'='*70}")
        print("✅ Entrenamiento completado para todas las loterías")
        print('='*70)
        return True
        
    except Exception as e:
        logger.error(f"Error en entrenamiento: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def ejecutar_prediccion(loteria: Optional[str] = None) -> bool:
    """
    3. Genera predicciones.
    
    Args:
        loteria: Nombre específico de lotería (opcional)
    """
    try:
        logger.info("="*70)
        logger.info("3. GENERACIÓN DE PREDICCIONES")
        logger.info("="*70)
        
        print(f"\n{'='*70}")
        print("3. GENERACIÓN DE PREDICCIONES")
        print('='*70)
        
        prediction_main(loteria)
        print("\n✅ Predicciones generadas")
        return True
    except Exception as e:
        logger.error(f"Error en predicción: {e}")
        print(f"\n❌ Error: {e}")
        return False


def ejecutar_pipeline_completo() -> bool:
    """Ejecuta el pipeline completo: actualizar → entrenar → predecir → limpiar."""
    print("\n" + "="*70)
    print("🎯 EJECUTANDO PIPELINE COMPLETO")
    print("="*70)
    
    pasos = [
        ("1. Actualización de Datos", lambda: ejecutar_actualizacion()),
        ("2. Entrenamiento de Modelos", lambda: ejecutar_entrenamiento()),
        ("3. Generación de Predicciones", lambda: ejecutar_prediccion()),
        ("4. Limpieza de Cache", lambda: ejecutar_limpieza())
    ]
    
    for nombre, funcion in pasos:
        print(f"\n{'='*70}")
        print(f"📍 {nombre}")
        print('='*70)
        
        if not funcion():
            print(f"\n❌ Pipeline detenido en: {nombre}")
            return False
    
    print("\n" + "="*70)
    print("🎉 Pipeline completado exitosamente")
    print("="*70)
    return True


def crear_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Sistema de Predicción de Lotería",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Ejemplos de uso:
            python main.py                          # Ejecuta pipeline completo
            python main.py --actualizar             # 1. Actualizar datos desde SuperAstro
            python main.py --entrenar               # 2. Entrenar modelos ML
            python main.py --predecir               # 3. Generar predicciones
            python main.py --limpiar                # 4. Limpiar cache de Python
            
            # Con filtros
            python main.py --actualizar --lottery luna     # Solo ASTRO LUNA
            python main.py --entrenar --lottery "ASTRO LUNA"  # Entrenar solo ASTRO LUNA
            python main.py --predecir --lottery ASTRO      # Predecir solo astros
        """
    )
    
    # Opciones principales
    parser.add_argument(
        '--actualizar',
        action='store_true',
        help='1. Actualizar datos desde SuperAstro (sitio oficial)'
    )
    
    parser.add_argument(
        '--entrenar',
        action='store_true',
        help='2. Entrenar modelos de Machine Learning'
    )
    
    parser.add_argument(
        '--predecir',
        action='store_true',
        help='3. Generar predicciones del próximo número ganador'
    )
    
    parser.add_argument(
        '--limpiar',
        action='store_true',
        help='4. Limpiar cache de Python (__pycache__)'
    )
    
    # Opciones adicionales
    parser.add_argument(
        '--lottery',
        type=str,
        help='Filtro de lotería (ej: astro, luna, sol)'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Mostrar configuración actual'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Sistema de Predicción de Lotería v2.0'
    )
    
    return parser


def mostrar_configuracion() -> None:
    """Muestra la configuración actual del sistema."""
    print("\n⚙️  CONFIGURACIÓN ACTUAL")
    print("="*50)
    print(f"API URL:        {settings.API_URL}")
    print(f"Lotería:        {settings.FIND_LOTERY}")
    print(f"Iteraciones:    {settings.ITERATIONS}")
    print(f"Min Accuracy:   {settings.MIN_ACCURACY}")
    print(f"Archivo Excel:  {settings.EXCEL_FILENAME}")
    print(f"Dir Modelos:    {settings.MODELS_DIR}")
    print(f"Dir Datos:      {settings.DATA_DIR}")
    print(f"Dir Logs:       {settings.LOGS_DIR}")
    print("="*50)


def main() -> int:
    """
    Función principal con CLI.
    
    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    parser = crear_parser()
    args = parser.parse_args()
    
    try:
        # Mostrar configuración
        if args.config:
            mostrar_configuracion()
            return 0
        
        # Si no hay argumentos, ejecutar pipeline completo
        if not any([args.actualizar, args.entrenar, args.predecir, args.limpiar]):
            return 0 if ejecutar_pipeline_completo() else 1
        
        # Ejecutar opciones individuales
        exito = True
        
        if args.actualizar:
            exito = ejecutar_actualizacion(filtro_loteria=args.lottery) and exito
        
        if args.entrenar:
            exito = ejecutar_entrenamiento(loteria=args.lottery) and exito
        
        if args.predecir:
            exito = ejecutar_prediccion(loteria=args.lottery) and exito
        
        if args.limpiar:
            exito = ejecutar_limpieza() and exito
        
        return 0 if exito else 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Ejecución interrumpida por el usuario")
        return 1
    
    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        print(f"\n❌ Error crítico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
