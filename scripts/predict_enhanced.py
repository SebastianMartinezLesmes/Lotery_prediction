"""
Script de Predicción Mejorada con Confianza Calibrada.

Usa modelos entrenados con el sistema mejorado para generar predicciones
con niveles de confianza calibrados.

Uso:
    python scripts/predict_enhanced.py
    python scripts/predict_enhanced.py --lottery "ASTRO LUNA"
    python scripts/predict_enhanced.py --confidence 0.7
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
import argparse
import joblib
import json
from datetime import datetime

from src.core.config import settings
from src.utils.ml_enhanced import EnhancedFeatureEngineer
from src.utils.zodiaco import obtener_zodiaco


def main():
    parser = argparse.ArgumentParser(
        description="Predicción Mejorada con Confianza Calibrada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PREDICCIÓN MEJORADA

Características:
  - Usa modelos calibrados con probabilidades confiables
  - Muestra nivel de confianza de cada predicción
  - Recomienda si apostar o no según confianza
  - Usa features de frecuencia y patrones

Ejemplos de uso:

  # Predecir todas las loterías
  python scripts/predict_enhanced.py

  # Lotería específica
  python scripts/predict_enhanced.py --lottery "ASTRO LUNA"

  # Con umbral de confianza personalizado
  python scripts/predict_enhanced.py --confidence 0.7

  # Guardar resultados
  python scripts/predict_enhanced.py --save
        """
    )
    
    parser.add_argument(
        '--lottery',
        type=str,
        help='Lotería específica a predecir'
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.6,
        help='Umbral mínimo de confianza (default: 0.6)'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Guardar resultados en JSON'
    )
    
    args = parser.parse_args()
    
    # Cargar datos históricos
    print("\nCargando datos históricos...")
    ruta_excel = settings.get_excel_path()
    
    if not ruta_excel.exists():
        print(f"ERROR: Archivo no encontrado: {ruta_excel}")
        print("   Ejecuta primero: python main.py --collect")
        return
    
    df = pd.read_excel(ruta_excel)
    
    # Preprocesar
    df = df.dropna(subset=["fecha", "lottery", "result", "series"])
    df["result"] = df["result"].astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
    df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
    
    # Obtener loterías
    if args.lottery:
        loterias = [args.lottery]
    else:
        loterias = df["lottery"].str.lower().unique()
    
    print(f"\n{'='*70}")
    print(f"PREDICCIÓN MEJORADA")
    print('='*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Loterías: {list(loterias)}")
    print(f"Umbral de confianza: {args.confidence}")
    print('='*70)
    
    resultados = []
    
    # Predecir cada lotería
    for nombre_loteria in loterias:
        print(f"\n{'='*70}")
        print(f">> {nombre_loteria.upper()}")
        print('='*70)
        
        df_loteria = df[df["lottery"].str.lower() == nombre_loteria.lower()].copy()
        
        if len(df_loteria) < 50:
            print(f"ADVERTENCIA: Datos insuficientes: {len(df_loteria)} registros")
            continue
        
        # Ordenar por fecha
        df_loteria = df_loteria.sort_values('fecha').reset_index(drop=True)
        
        # Predecir
        resultado = predecir_loteria_mejorada(
            df=df_loteria,
            lottery_name=nombre_loteria,
            confidence_threshold=args.confidence
        )
        
        if resultado:
            resultados.append(resultado)
            mostrar_resultado(resultado, args.confidence)
    
    # Guardar resultados si se solicita
    if args.save and resultados:
        output_file = settings.DATA_DIR / f"predictions_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        print(f"\n{'='*70}")
        print(f"Resultados guardados en: {output_file}")
        print('='*70)


def predecir_loteria_mejorada(
    df: pd.DataFrame,
    lottery_name: str,
    confidence_threshold: float
) -> dict:
    """
    Genera predicción mejorada para una lotería.
    
    Args:
        df: DataFrame con datos históricos
        lottery_name: Nombre de la lotería
        confidence_threshold: Umbral de confianza
    
    Returns:
        Diccionario con resultados de predicción
    """
    # Cargar modelos
    model_result_path = settings.MODELS_DIR / f"modelo_result_{lottery_name.lower().replace(' ', '_')}.pkl"
    model_series_path = settings.MODELS_DIR / f"modelo_series_{lottery_name.lower().replace(' ', '_')}.pkl"
    
    if not model_result_path.exists() or not model_series_path.exists():
        print(f"ERROR: Modelos no encontrados para {lottery_name}")
        print("   Entrena primero con: python scripts/train_enhanced.py")
        return None
    
    # Cargar metadata
    metadata_result_path = settings.MODELS_DIR / f"metadata_result_{lottery_name.lower().replace(' ', '_')}.json"
    metadata_series_path = settings.MODELS_DIR / f"metadata_series_{lottery_name.lower().replace(' ', '_')}.json"
    
    use_frequency_result = True
    use_frequency_series = True
    feature_cols_result = None
    feature_cols_series = None
    
    if metadata_result_path.exists():
        with open(metadata_result_path, 'r') as f:
            metadata = json.load(f)
            use_frequency_result = metadata.get('use_frequency', True)
            feature_cols_result = metadata.get('feature_cols')
    
    if metadata_series_path.exists():
        with open(metadata_series_path, 'r') as f:
            metadata = json.load(f)
            use_frequency_series = metadata.get('use_frequency', True)
            feature_cols_series = metadata.get('feature_cols')
    
    # Cargar modelos
    model_result = joblib.load(model_result_path)
    model_series = joblib.load(model_series_path)
    
    # Generar features para RESULT
    feature_engineer_result = EnhancedFeatureEngineer(target_col='result')
    df_features_result = feature_engineer_result.create_all_features(
        df,
        include_frequency=use_frequency_result,
        include_temporal=True
    )
    
    # Generar features para SERIES
    feature_engineer_series = EnhancedFeatureEngineer(target_col='series')
    df_features_series = feature_engineer_series.create_all_features(
        df,
        include_frequency=use_frequency_series,
        include_temporal=True
    )
    
    # Preparar features para hoy
    hoy = datetime.today()
    
    # Features para RESULT
    if feature_cols_result:
        X_result = df_features_result[feature_cols_result].fillna(0).iloc[[-1]].values
    else:
        feature_cols = [col for col in df_features_result.columns 
                       if col not in ['fecha', 'lottery', 'slug', 'result', 'series'] 
                       and df_features_result[col].dtype in [np.int64, np.float64]]
        X_result = df_features_result[feature_cols].fillna(0).iloc[[-1]].values
    
    # Features para SERIES
    if feature_cols_series:
        X_series = df_features_series[feature_cols_series].fillna(0).iloc[[-1]].values
    else:
        feature_cols = [col for col in df_features_series.columns 
                       if col not in ['fecha', 'lottery', 'slug', 'result', 'series'] 
                       and df_features_series[col].dtype in [np.int64, np.float64]]
        X_series = df_features_series[feature_cols].fillna(0).iloc[[-1]].values
    
    # Predecir con confianza
    if hasattr(model_result, 'predict_with_confidence'):
        # Modelo calibrado
        pred_result, conf_result, is_conf_result = model_result.predict_with_confidence(
            X_result,
            confidence_threshold=confidence_threshold
        )
        numero = pred_result[0]
        confianza_numero = conf_result[0]
        es_confiable_numero = is_conf_result[0]
    else:
        # Modelo sin calibrar
        numero = model_result.predict(X_result)[0]
        if hasattr(model_result, 'predict_proba'):
            probas = model_result.predict_proba(X_result)
            confianza_numero = np.max(probas)
        else:
            confianza_numero = 0.5
        es_confiable_numero = confianza_numero >= confidence_threshold
    
    if hasattr(model_series, 'predict_with_confidence'):
        # Modelo calibrado
        pred_series, conf_series, is_conf_series = model_series.predict_with_confidence(
            X_series,
            confidence_threshold=confidence_threshold
        )
        simbolo_codificado = pred_series[0]
        confianza_simbolo = conf_series[0]
        es_confiable_simbolo = is_conf_series[0]
    else:
        # Modelo sin calibrar
        simbolo_codificado = model_series.predict(X_series)[0]
        if hasattr(model_series, 'predict_proba'):
            probas = model_series.predict_proba(X_series)
            confianza_simbolo = np.max(probas)
        else:
            confianza_simbolo = 0.5
        es_confiable_simbolo = confianza_simbolo >= confidence_threshold
    
    # Decodificar símbolo
    simbolo = obtener_zodiaco(simbolo_codificado)
    
    # Calcular confianza general
    confianza_general = (confianza_numero + confianza_simbolo) / 2
    es_confiable_general = es_confiable_numero and es_confiable_simbolo
    
    return {
        'loteria': lottery_name,
        'fecha_prediccion': hoy.strftime('%Y-%m-%d'),
        'numero': int(numero),
        'numero_formateado': str(numero).zfill(4),
        'simbolo': simbolo,
        'confianza_numero': float(confianza_numero),
        'confianza_simbolo': float(confianza_simbolo),
        'confianza_general': float(confianza_general),
        'es_confiable_numero': bool(es_confiable_numero),
        'es_confiable_simbolo': bool(es_confiable_simbolo),
        'es_confiable_general': bool(es_confiable_general),
        'recomendacion': 'APOSTAR' if es_confiable_general else 'NO APOSTAR'
    }


def mostrar_resultado(resultado: dict, threshold: float):
    """Muestra el resultado de predicción formateado."""
    print(f"\nNúmero: {resultado['numero_formateado']}")
    print(f"   Confianza: {resultado['confianza_numero']:.2%}")
    print(f"   Estado: {'CONFIABLE' if resultado['es_confiable_numero'] else 'BAJA CONFIANZA'}")
    
    print(f"\nSímbolo: {resultado['simbolo']}")
    print(f"   Confianza: {resultado['confianza_simbolo']:.2%}")
    print(f"   Estado: {'CONFIABLE' if resultado['es_confiable_simbolo'] else 'BAJA CONFIANZA'}")
    
    print(f"\nConfianza General: {resultado['confianza_general']:.2%}")
    
    # Recomendación
    if resultado['es_confiable_general']:
        print(f"\nRECOMENDACIÓN: APOSTAR")
        print(f"   La predicción supera el umbral de confianza ({threshold:.0%})")
    else:
        print(f"\nRECOMENDACIÓN: NO APOSTAR")
        print(f"   La predicción NO supera el umbral de confianza ({threshold:.0%})")
        print(f"   Considera esperar a una predicción más confiable")


if __name__ == "__main__":
    main()
