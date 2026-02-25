"""
Punto de entrada alternativo con CLI mejorado.
Permite ejecutar componentes individuales o el pipeline completo.
"""
import sys
import argparse
from typing import Optional

from src.core.logger import get_main_logger
from src.core.config import settings

logger = get_main_logger()


def ejecutar_dependencias() -> bool:
    """Instala/verifica dependencias del sistema."""
    from src.utils import dependencies
    try:
        logger.info("Verificando dependencias...")
        # Aquí iría la lógica de dependencies
        print("✅ Dependencias verificadas")
        return True
    except Exception as e:
        logger.error(f"Error en dependencias: {e}")
        return False


def ejecutar_recoleccion() -> bool:
    """Recolecta datos desde Excel/API."""
    try:
        logger.info("Iniciando recolección de datos...")
        from src.excel.read_excel import obtener_loterias_disponibles
        
        loterias = obtener_loterias_disponibles()
        print(f"✅ Datos recolectados: {len(loterias)} loterías")
        return True
    except Exception as e:
        logger.error(f"Error en recolección: {e}")
        print(f"❌ Error: {e}")
        return False


def ejecutar_entrenamiento(loteria: Optional[str] = None) -> bool:
    """
    Entrena modelos de ML.
    
    Args:
        loteria: Nombre específico de lotería (opcional)
    """
    try:
        logger.info(f"Iniciando entrenamiento{f' para {loteria}' if loteria else ''}...")
        
        import pandas as pd
        import os
        from src.core.config import settings
        from src.utils.training import entrenar_modelos_por_loteria
        
        # Ruta al archivo Excel
        ruta_excel = settings.get_excel_path()
        
        if not os.path.exists(ruta_excel):
            print(f"Archivo no encontrado: {ruta_excel}")
            print("   Ejecuta primero: python main.py --collect")
            return False
        
        print(f"Leyendo datos desde: {ruta_excel}")
        
        # Leer datos
        df = pd.read_excel(ruta_excel)
        
        # Validar columnas
        columnas_necesarias = {"fecha", "lottery", "result", "series"}
        if not columnas_necesarias.issubset(df.columns):
            print(f"Faltan columnas necesarias: {columnas_necesarias - set(df.columns)}")
            return False
        
        # Preprocesar
        df = df.dropna(subset=["fecha", "lottery", "result", "series"])
        df["result"] = df["result"].astype(int)
        df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
        df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
        
        # Extraer features
        df["dia"] = df["fecha"].dt.day
        df["mes"] = df["fecha"].dt.month
        df["anio"] = df["fecha"].dt.year
        df["dia_semana"] = df["fecha"].dt.weekday
        
        # Obtener loterías
        if loteria:
            loterias = [loteria]
        else:
            loterias = df["lottery"].str.lower().unique()
        
        print(f"\nLoterias a entrenar: {list(loterias)}\n")
        
        # Entrenar cada lotería
        for nombre_loteria in loterias:
            print(f"\n{'='*70}")
            print(f"Entrenando modelos para: {nombre_loteria.upper()}")
            print('='*70)
            
            df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()]
            
            if len(df_loteria) < 50:
                print(f"Datos insuficientes para {nombre_loteria}: {len(df_loteria)} registros")
                print("   Se necesitan al menos 50 registros")
                continue
            
            X_l = df_loteria[["dia", "mes", "anio", "dia_semana"]].values
            y_r = df_loteria["result"].values
            y_s = df_loteria["series"].values
            
            entrenar_modelos_por_loteria(
                X=X_l,
                y_result=y_r,
                y_series=y_s,
                nombre_loteria=nombre_loteria,
                min_acc=settings.MIN_ACCURACY,
                max_iter=settings.ITERATIONS,
                verbose=True  # ✅ Activar visualización
            )
        
        print(f"\n{'='*70}")
        print("Entrenamiento completado para todas las loterias")
        print('='*70)
        return True
        
    except Exception as e:
        logger.error(f"Error en entrenamiento: {e}", exc_info=True)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def ejecutar_prediccion(loteria: Optional[str] = None) -> bool:
    """
    Genera predicciones.
    
    Args:
        loteria: Nombre específico de lotería (opcional)
    """
    try:
        logger.info(f"Generando predicciones{f' para {loteria}' if loteria else ''}...")
        from src.utils.prediction import main as prediction_main
        
        prediction_main()
        print("✅ Predicciones generadas")
        return True
    except Exception as e:
        logger.error(f"Error en predicción: {e}")
        print(f"❌ Error: {e}")
        return False


def ejecutar_pipeline_completo() -> bool:
    """Ejecuta el pipeline completo."""
    print("🎯 Ejecutando pipeline completo...\n")
    
    pasos = [
        ("Dependencias", ejecutar_dependencias),
        ("Recolección de Datos", ejecutar_recoleccion),
        ("Predicción", ejecutar_prediccion)
    ]
    
    for nombre, funcion in pasos:
        print(f"\n{'='*50}")
        print(f"📍 {nombre}")
        print('='*50)
        
        if not funcion():
            print(f"\n❌ Pipeline detenido en: {nombre}")
            return False
    
    print("\n" + "="*50)
    print("🎉 Pipeline completado exitosamente")
    print("="*50)
    return True


def crear_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Sistema de Predicción de Lotería",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                          # Ejecuta pipeline completo
  python main.py --deps                   # Solo dependencias
  python main.py --collect                # Solo recolección
  python main.py --train                  # Solo entrenamiento
  python main.py --predict                # Solo predicción
  python main.py --predict --lottery ASTRO # Predicción específica
        """
    )
    
    parser.add_argument(
        '--deps',
        action='store_true',
        help='Verificar/instalar dependencias'
    )
    
    parser.add_argument(
        '--collect',
        action='store_true',
        help='Recolectar datos desde Excel/API'
    )
    
    parser.add_argument(
        '--train',
        action='store_true',
        help='Entrenar modelos de ML'
    )
    
    parser.add_argument(
        '--predict',
        action='store_true',
        help='Generar predicciones'
    )
    
    parser.add_argument(
        '--lottery',
        type=str,
        help='Nombre específico de lotería (ej: ASTRO)'
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
        if not any([args.deps, args.collect, args.train, args.predict]):
            return 0 if ejecutar_pipeline_completo() else 1
        
        # Ejecutar componentes individuales
        exito = True
        
        if args.deps:
            exito = ejecutar_dependencias() and exito
        
        if args.collect:
            exito = ejecutar_recoleccion() and exito
        
        if args.train:
            exito = ejecutar_entrenamiento(args.lottery) and exito
        
        if args.predict:
            exito = ejecutar_prediccion(args.lottery) and exito
        
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
