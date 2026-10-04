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
from src.utils.drop_cache import main as drop_cache_main
from src.utils.prediction import main as prediction_main
from src.utils.training_simple import entrenar_modelos_por_loteria
from src.features.feature_engineering import generar_features

logger = get_main_logger()

def log_y_mostrar(msg: str) -> None:
    """Emite el mensaje al logger y a stdout."""
    logger.info(msg)
    print(msg)

def ejecutar_limpieza() -> bool:
    """4. Limpia archivos de caché de Python."""
    try:
        log_y_mostrar("="*70)
        log_y_mostrar("4. LIMPIEZA DE CACHE")
        log_y_mostrar("="*70)
        
        drop_cache_main()
        
        print("\n✅ Limpieza completada")
        return True
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        print(f"\n❌ Error: {e}")
        return False


def ejecutar_actualizacion(filtro_loteria: Optional[str] = None) -> bool:
    """
    1. Sincroniza datos desde SuperAstro hacia Neon PostgreSQL.

    Args:
        filtro_loteria: Filtro para loterías (ej: "astro", "luna", "sol")
    """
    try:
        log_y_mostrar("=" * 70)
        log_y_mostrar("1. SINCRONIZACIÓN DE DATOS CON NEON POSTGRESQL")
        log_y_mostrar("=" * 70)
        log_y_mostrar(f"Fuente: SuperAstro (sitio oficial)")
        log_y_mostrar(f"Destino: Neon PostgreSQL")
        if filtro_loteria:
            log_y_mostrar(f"Filtro: {filtro_loteria}")
        log_y_mostrar('='*70)

        from src.database.sync import synchronize_database

        total = synchronize_database(filtro_loteria=filtro_loteria)

        print(f"\n✅ Sincronización completada: {total} registros insertados/actualizados en Neon")
        return True

    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        print(f"\n❌ Error: {e}")
        return False


def ejecutar_entrenamiento(
    loteria: Optional[str] = None,
    modo: Optional[str] = None,
    sincronizar: bool = True,
) -> bool:
    """
    2. Entrena modelos de ML con features avanzadas.

    Args:
        loteria: Nombre específico de lotería (opcional)
        modo: 'test' o 'prod'. Si no se pasa, usa TRAINING_MODE del entorno.
        sincronizar: Si True (default), sincroniza con Neon antes de entrenar.
    """
    try:
        modo_activo = (modo.lower() if modo else os.getenv('TRAINING_MODE', 'prod')).upper()

        log_y_mostrar("="*70)
        log_y_mostrar(f"2. ENTRENAMIENTO DE MODELOS  [modo: {modo_activo}]")
        log_y_mostrar("="*70)

        # ── Sincronizar con Neon antes de entrenar (si no viene del pipeline) ──
        if sincronizar:
            try:
                from src.database.sync import synchronize_database
                logger.info("Sincronizando con Neon antes del entrenamiento...")
                synchronize_database(filtro_loteria=loteria)
            except Exception as e_sync:
                logger.warning(f"Sincronización con Neon falló (se usará Excel): {e_sync}")

        # ── Intentar cargar desde Neon ──────────────────────────────
        df = None
        try:
            from src.database.connection import NeonConnection
            from src.database.repository import LotteriaRepository

            conn = NeonConnection()
            try:
                repository = LotteriaRepository(conn)

                # T12: use settings.LOTTERIES instead of hardcoded list
                loterias_neon = list(settings.LOTTERIES)
                if loteria:
                    loterias_neon = [l for l in loterias_neon if loteria.upper() in l.upper()]

                frames = []
                for lot in loterias_neon:
                    try:
                        df_lot = repository.get_all_results(lot)
                        if not df_lot.empty:
                            frames.append(df_lot)
                    except Exception as e_lot:
                        logger.warning(f"No se pudo cargar {lot} desde Neon: {e_lot}")

                if frames:
                    df = pd.concat(frames, ignore_index=True)
                    logger.info(f"Datos cargados desde Neon: {len(df)} registros")
                    print(f"Leyendo datos desde: Neon PostgreSQL ({len(df)} registros)")
            finally:
                conn.close()
        except Exception as e_neon:
            logger.warning(f"Fallo al cargar datos desde Neon, usando Excel: {e_neon}")
            df = None

        # ── Fallback a Excel ────────────────────────────────────────
        if df is None or df.empty:
            ruta_excel = settings.get_excel_path()
            if not os.path.exists(ruta_excel):
                print(f"❌ Archivo no encontrado: {ruta_excel}")
                print("   Ejecuta primero: python main.py --actualizar")
                return False
            print(f"Leyendo datos desde: {ruta_excel} (fallback Excel)")
            df = pd.read_excel(ruta_excel)

        # ── Validar columnas ────────────────────────────────────────
        columnas_necesarias = {"fecha", "lottery", "result", "series"}
        if not columnas_necesarias.issubset(df.columns):
            print(f"❌ Faltan columnas necesarias: {columnas_necesarias - set(df.columns)}")
            return False

        # Preprocesar
        df = df.dropna(subset=["fecha", "lottery", "result", "series"])
        df["result"] = df["result"].astype(int)
        df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
        # T8: fixed categories encoding for series
        df["series"] = pd.Categorical(
            df["series"].astype(str).str.upper(),
            categories=settings.SIGNOS
        ).codes

        # Obtener loterías
        if loteria:
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
        print(f"Features: Históricas (lags + rolling + frecuencia + días sin aparecer)")
        print('='*70)

        # Entrenar cada lotería
        for nombre_loteria in loterias:
            print(f"\n{'='*70}")
            print(f"Entrenando modelos para: {nombre_loteria.upper()}")
            print('='*70)

            df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()].copy()

            min_rec = settings.TRAINING_CONFIGURE["min_records"]
            if len(df_loteria) < min_rec:
                print(f"❌ Datos insuficientes para {nombre_loteria}: {len(df_loteria)} registros")
                print(f"   Se necesitan al menos {min_rec} registros")
                continue

            # Ordenar por fecha
            df_loteria = df_loteria.sort_values("fecha").reset_index(drop=True)
            df_loteria["fecha"] = pd.to_datetime(df_loteria["fecha"])

            # T10: staleness check
            ultima_fecha = df_loteria["fecha"].max()
            dias = (pd.Timestamp.now() - ultima_fecha).days
            if dias > 7:
                logger.warning(
                    f"{nombre_loteria}: datos desactualizados — "
                    f"última fecha {ultima_fecha.date()} ({dias} días)"
                )

            # Generar features históricas (sin calendario)
            X_df = generar_features(df_loteria)
            X_df = X_df.replace([np.inf, -np.inf], np.nan).dropna()

            # T7: align target by index instead of tail()
            df_loteria = df_loteria.loc[X_df.index]
            X_l = X_df.values
            y_r = df_loteria["result"].values
            y_s = df_loteria["series"].values
            cols = list(X_df.columns)

            print(f"\nDatos preparados:")
            print(f"  Registros : {X_l.shape[0]}")
            print(f"  Features  : {X_l.shape[1]}")
            print(f"  Features  : {', '.join(cols[:5])}... (+{len(cols)-5} más)")

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
        log_y_mostrar("="*70)
        log_y_mostrar("3. GENERACIÓN DE PREDICCIONES")
        log_y_mostrar("="*70)
        
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
        ("2. Entrenamiento de Modelos", lambda: ejecutar_entrenamiento(sincronizar=False)),
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
        '--modo',
        type=str,
        choices=['test', 'prod'],
        help='Modo de entrenamiento: test (rápido) o prod (completo). '
             'Sobreescribe TRAINING_MODE del .env'
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
    profile = settings.get_training_profile()
    print("\n⚙️  CONFIGURACIÓN ACTUAL")
    print("="*50)
    print(f"API URL:        {settings.API_URL}")
    print(f"Loterías:       {settings.LOTTERIES}")
    print(f"Modo entreno:   {settings.TRAINING_MODE.upper()}")
    print(f"Iteraciones:    {profile['max_iter']}")
    print(f"Min Accuracy:   {profile['min_accuracy']}")
    print(f"n_estimators:   {profile['n_estimators']}")
    print(f"max_depth:      {profile['max_depth']}")
    print(f"test_size:      {profile['test_size']}")
    print(f"min_records:    {profile['min_records']}")
    print(f"Dir Modelos:    {settings.MODELS_DIR}")
    print(f"Dir Datos:      {settings.DATA_DIR}")
    print(f"Database URL:   {'configurado' if settings.DATABASE_URL else 'NO configurado'}")
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
            exito = ejecutar_entrenamiento(loteria=args.lottery, modo=getattr(args, 'modo', None)) and exito
        
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
