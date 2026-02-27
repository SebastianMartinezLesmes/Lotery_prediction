"""
Script para entrenar modelos usando el sistema evolutivo.
Mantiene múltiples variantes que compiten y evolucionan.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import argparse
from src.core.config import settings
from src.utils.evolutionary_training import entrenar_evolutivo, EvolutionaryTrainer


def main():
    parser = argparse.ArgumentParser(
        description="Entrenamiento Evolutivo de Modelos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Entrenar todas las loterías
  python scripts/train_evolutionary.py

  # Entrenar lotería específica
  python scripts/train_evolutionary.py --lottery "ASTRO LUNA"

  # Con más iteraciones
  python scripts/train_evolutionary.py --iterations 20000

  # Ver estado de variantes
  python scripts/train_evolutionary.py --status

Características:
  - Mantiene 3 variantes de modelos
  - Variante #1: PRODUCTION (mejor modelo)
  - Variantes #2 y #3: EXPERIMENTAL (exploran alternativas)
  - Si una experimental supera a production, se intercambian
  - Mutación automática de experimentales sin mejora
  - Evolución continua sin reiniciar
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
    
    # Extraer features
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    
    # Obtener loterías
    if args.lottery:
        loterias = [args.lottery]
    else:
        loterias = df["lottery"].str.lower().unique()
    
    print(f"\n{'='*70}")
    print(f"ENTRENAMIENTO EVOLUTIVO")
    print('='*70)
    print(f"Loterías: {list(loterias)}")
    print(f"Iteraciones máximas: {args.iterations}")
    print(f"Patience: {args.patience}")
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
        
        X = df_loteria[["dia", "mes", "anio", "dia_semana"]].values
        y_result = df_loteria["result"].values
        y_series = df_loteria["series"].values
        
        # Entrenar evolutivamente
        results = entrenar_evolutivo(
            X=X,
            y_result=y_result,
            y_series=y_series,
            lottery_name=nombre_loteria,
            max_iterations=args.iterations,
            patience=args.patience,
            verbose=True
        )
        
        print(f"\n✅ Entrenamiento completado para {nombre_loteria}")
        print(f"   Result: Acc={results['result']['accuracy']:.4f}, "
              f"F1={results['result']['f1_score']:.4f}")
        print(f"   Series: Acc={results['series']['accuracy']:.4f}, "
              f"F1={results['series']['f1_score']:.4f}")
    
    print(f"\n{'='*70}")
    print("🎉 ENTRENAMIENTO EVOLUTIVO COMPLETADO")
    print('='*70)
    print("\nPara ver el estado de las variantes:")
    print("  python scripts/train_evolutionary.py --status")


def mostrar_estado_variantes(lottery: str = None):
    """Muestra el estado actual de las variantes."""
    print(f"\n{'='*70}")
    print("ESTADO DE VARIANTES")
    print('='*70)
    
    # Buscar archivos de variantes
    variants_files = list(settings.MODELS_DIR.glob("variants_*.json"))
    
    if not variants_files:
        print("\n⚠️  No se encontraron variantes entrenadas")
        print("   Ejecuta primero: python scripts/train_evolutionary.py")
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
        lottery_name = ' '.join(parts[1:-1])
        model_type = parts[-1]
        
        # Crear trainer para cargar variantes
        trainer = EvolutionaryTrainer(
            lottery_name=lottery_name,
            model_type=model_type,
            max_iterations=1
        )
        
        # Mostrar resumen
        print(trainer.get_variants_summary())


if __name__ == "__main__":
    main()
