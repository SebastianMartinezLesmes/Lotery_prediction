"""
Script para entrenar modelos usando el sistema híbrido MEJORADO.
Combina múltiples algoritmos (RF, XGBoost, LightGBM) con TODAS las mejoras de ML:
- Features de frecuencia y patrones (números calientes/fríos)
- Calibración de probabilidades (confianza real)
- Optimización bayesiana (mejores hiperparámetros)
- Evolución continua
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import argparse
from src.core.config import settings
from src.utils.hybrid_training import entrenar_hibrido, HybridTrainer


def main():
    parser = argparse.ArgumentParser(
        description="Entrenamiento Híbrido MEJORADO - El Mejor Sistema Disponible",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 ENTRENAMIENTO HÍBRIDO MEJORADO

Combina TODAS las mejoras de ML:
  ✓ Múltiples algoritmos (RandomForest, XGBoost, LightGBM)
  ✓ Feature engineering avanzado (40+ features)
  ✓ Features de frecuencia y patrones (números calientes/fríos)
  ✓ Calibración de probabilidades (confianza real)
  ✓ Optimización bayesiana (mejores hiperparámetros)
  ✓ Evolución continua (3 variantes compitiendo)
  ✓ Sin reinicio (continúa desde estado guardado)

Variantes:
  🏆 Variante #1: RandomForest (rápido, robusto)
  🧪 Variante #2: XGBoost (preciso, potente)
  🧪 Variante #3: LightGBM (eficiente, rápido)

El mejor algoritmo siempre está en producción.
Los modelos incluyen calibración de probabilidades.

Ejemplos de uso:

  # Entrenar con TODAS las mejoras (recomendado)
  python scripts/train_hybrid.py

  # Lotería específica
  python scripts/train_hybrid.py --lottery "ASTRO LUNA"

  # Sin calibración (más rápido)
  python scripts/train_hybrid.py --no-calibration

  # Sin optimización bayesiana (más rápido)
  python scripts/train_hybrid.py --no-bayesian

  # Sin features de frecuencia (más rápido)
  python scripts/train_hybrid.py --no-frequency

  # Más iteraciones de optimización bayesiana (mejor resultado)
  python scripts/train_hybrid.py --bayesian-iter 50

  # Ver estado de variantes
  python scripts/train_hybrid.py --status
        """
    )
    
    parser.add_argument(
        '--lottery',
        type=str,
        help='Lotería específica a entrenar'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=10000,
        help='Número máximo de iteraciones (default: 10000)'
    )
    
    parser.add_argument(
        '--patience',
        type=int,
        default=100,
        help='Iteraciones sin mejora antes de early stopping (default: 100)'
    )
    
    parser.add_argument(
        '--no-features',
        action='store_true',
        help='Desactivar feature engineering avanzado (más rápido)'
    )
    
    parser.add_argument(
        '--no-frequency',
        action='store_true',
        help='Desactivar features de frecuencia (más rápido)'
    )
    
    parser.add_argument(
        '--no-calibration',
        action='store_true',
        help='Desactivar calibración de probabilidades (más rápido)'
    )
    
    parser.add_argument(
        '--no-bayesian',
        action='store_true',
        help='Desactivar optimización bayesiana (más rápido)'
    )
    
    parser.add_argument(
        '--bayesian-iter',
        type=int,
        default=30,
        help='Iteraciones de optimización bayesiana (default: 30)'
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.6,
        help='Umbral de confianza para calibración (default: 0.6)'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Mostrar estado actual de las variantes'
    )
    
    args = parser.parse_args()
    
    # Mostrar estado si se solicita
    if args.status:
        mostrar_estado_variantes(args.lottery)
        return
    
    # Cargar datos
    print("Cargando datos...")
    ruta_excel = settings.get_excel_path()
    
    if not ruta_excel.exists():
        print(f"❌ Archivo no encontrado: {ruta_excel}")
        print("   Ejecuta primero: python main.py --collect")
        return
    
    df = pd.read_excel(ruta_excel)
    
    # Validar columnas
    columnas_necesarias = {"fecha", "lottery", "result", "series"}
    if not columnas_necesarias.issubset(df.columns):
        print(f"❌ Faltan columnas: {columnas_necesarias - set(df.columns)}")
        return
    
    # Preprocesar
    df = df.dropna(subset=["fecha", "lottery", "result", "series"])
    df["result"] = df["result"].astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
    df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
    
    # Extraer features básicos
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    
    # Obtener loterías
    if args.lottery:
        loterias = [args.lottery]
    else:
        loterias = df["lottery"].str.lower().unique()
    
    use_features = not args.no_features
    use_frequency = not args.no_frequency
    use_calibration = not args.no_calibration
    use_bayesian = not args.no_bayesian
    
    print(f"\n{'='*70}")
    print(f"🚀 ENTRENAMIENTO HÍBRIDO MEJORADO")
    print('='*70)
    print(f"Loterías: {list(loterias)}")
    print(f"Iteraciones máximas: {args.iterations}")
    print(f"Patience: {args.patience}")
    print(f"Feature engineering avanzado: {'✓ Activado' if use_features else '✗ Desactivado'}")
    print(f"Features de frecuencia: {'✓ Activado' if use_frequency else '✗ Desactivado'}")
    print(f"Calibración de probabilidades: {'✓ Activado' if use_calibration else '✗ Desactivado'}")
    print(f"Optimización bayesiana: {'✓ Activado' if use_bayesian else '✗ Desactivado'}")
    if use_bayesian:
        print(f"Iteraciones bayesianas: {args.bayesian_iter}")
    if use_calibration:
        print(f"Umbral de confianza: {args.confidence}")
    print(f"Algoritmos: RandomForest, XGBoost, LightGBM")
    print('='*70)
    
    # Entrenar cada lotería
    for nombre_loteria in loterias:
        print(f"\n{'='*70}")
        print(f"🎯 {nombre_loteria.upper()}")
        print('='*70)
        
        df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()]
        
        if len(df_loteria) < 50:
            print(f"⚠️  Datos insuficientes: {len(df_loteria)} registros")
            print("   Se necesitan al menos 50 registros")
            continue
        
        print(f"Registros disponibles: {len(df_loteria)}")
        
        # Ordenar por fecha para features de frecuencia
        df_loteria = df_loteria.sort_values('fecha').reset_index(drop=True)
        
        X = df_loteria[["dia", "mes", "anio", "dia_semana"]].values
        y_result = df_loteria["result"].values
        y_series = df_loteria["series"].values
        
        # Entrenar híbridamente con TODAS las mejoras
        results = entrenar_hibrido(
            X=X,
            y_result=y_result,
            y_series=y_series,
            lottery_name=nombre_loteria,
            df_original=df_loteria if use_frequency else None,
            max_iterations=args.iterations,
            patience=args.patience,
            use_advanced_features=use_features,
            use_frequency_features=use_frequency,
            use_calibration=use_calibration,
            use_bayesian_optimization=use_bayesian,
            bayesian_iterations=args.bayesian_iter,
            confidence_threshold=args.confidence,
            verbose=True
        )
        
        # Mostrar resultados
        result_trainer = results['result']['trainer']
        series_trainer = results['series']['trainer']
        
        result_prod = result_trainer._get_production_variant()
        series_prod = series_trainer._get_production_variant()
        
        print(f"\n✅ Entrenamiento completado para {nombre_loteria}")
        print(f"\n   Result:")
        print(f"      Algoritmo ganador: {result_prod.algorithm}")
        print(f"      Calibrado: {'Sí' if result_prod.is_calibrated else 'No'}")
        print(f"      Accuracy: {result_prod.accuracy:.4f}")
        print(f"      F1-Score: {result_prod.f1_score:.4f}")
        print(f"\n   Series:")
        print(f"      Algoritmo ganador: {series_prod.algorithm}")
        print(f"      Calibrado: {'Sí' if series_prod.is_calibrated else 'No'}")
        print(f"      Accuracy: {series_prod.accuracy:.4f}")
        print(f"      F1-Score: {series_prod.f1_score:.4f}")
    
    print(f"\n{'='*70}")
    print("🎉 ENTRENAMIENTO HÍBRIDO MEJORADO COMPLETADO")
    print('='*70)
    print("\nMejoras aplicadas:")
    if use_features:
        print("  ✓ Feature engineering avanzado (40+ features)")
    if use_frequency:
        print("  ✓ Features de frecuencia y patrones")
    if use_calibration:
        print("  ✓ Calibración de probabilidades")
    if use_bayesian:
        print("  ✓ Optimización bayesiana")
    print("\nPara ver el estado de las variantes:")
    print("  python scripts/train_hybrid.py --status")
    print("\nPara continuar evolucionando (sin reiniciar):")
    print("  python scripts/train_hybrid.py")


def mostrar_estado_variantes(lottery: str = None):
    """Muestra el estado actual de las variantes híbridas."""
    print(f"\n{'='*70}")
    print("ESTADO DE VARIANTES HÍBRIDAS")
    print('='*70)
    
    # Buscar archivos de variantes
    variants_files = list(settings.MODELS_DIR.glob("hybrid_variants_*.json"))
    
    if not variants_files:
        print("\n⚠️  No se encontraron variantes híbridas entrenadas")
        print("   Ejecuta primero: python scripts/train_hybrid.py")
        return
    
    # Filtrar por lotería si se especifica
    if lottery:
        variants_files = [f for f in variants_files if lottery.lower().replace(" ", "_") in f.name.lower()]
    
    if not variants_files:
        print(f"\n⚠️  No se encontraron variantes para: {lottery}")
        return
    
    # Mostrar cada archivo
    for variants_file in sorted(variants_files):
        # Extraer nombre de lotería y tipo
        parts = variants_file.stem.split('_')
        lottery_name = ' '.join(parts[2:-1])
        model_type = parts[-1]
        
        # Crear trainer para cargar variantes
        trainer = HybridTrainer(
            lottery_name=lottery_name,
            model_type=model_type,
            max_iterations=1
        )
        
        # Mostrar resumen
        print(trainer.get_variants_summary())


if __name__ == "__main__":
    main()
