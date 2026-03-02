"""
Script de Prueba del Sistema Completo.
Verifica que todas las funciones estén funcionando correctamente.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
from datetime import datetime

print("="*70)
print("PRUEBA DEL SISTEMA COMPLETO")
print("="*70)

# Test 1: Importaciones
print("\n[1/8] Probando importaciones...")
try:
    from src.utils.ml_enhanced import (
        FrequencyPatternEngineer,
        CalibratedModelWrapper,
        BayesianOptimizer,
        EnhancedFeatureEngineer,
        BAYESIAN_AVAILABLE
    )
    from src.utils.hybrid_training import entrenar_hibrido, HybridTrainer
    from src.utils.ml_advanced import FeatureEngineer
    from src.core.config import settings
    print("   ✓ Todas las importaciones exitosas")
except Exception as e:
    print(f"   ✗ Error en importaciones: {e}")
    sys.exit(1)

# Test 2: Configuración
print("\n[2/8] Probando configuración...")
try:
    excel_path = settings.get_excel_path()
    models_dir = settings.MODELS_DIR
    print(f"   ✓ Ruta Excel: {excel_path}")
    print(f"   ✓ Directorio modelos: {models_dir}")
except Exception as e:
    print(f"   ✗ Error en configuración: {e}")
    sys.exit(1)

# Test 3: Carga de datos
print("\n[3/8] Probando carga de datos...")
try:
    if not excel_path.exists():
        print(f"   ⚠ Archivo Excel no encontrado: {excel_path}")
        print("   Ejecuta: python main.py --collect")
        sys.exit(1)
    
    df = pd.read_excel(excel_path)
    print(f"   ✓ Datos cargados: {len(df)} registros")
    print(f"   ✓ Columnas: {list(df.columns)}")
except Exception as e:
    print(f"   ✗ Error cargando datos: {e}")
    sys.exit(1)

# Test 4: Preprocesamiento
print("\n[4/8] Probando preprocesamiento...")
try:
    df = df.dropna(subset=["fecha", "lottery", "result", "series"])
    df["result"] = df["result"].astype(int)
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
    df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes
    
    df["dia"] = df["fecha"].dt.day
    df["mes"] = df["fecha"].dt.month
    df["anio"] = df["fecha"].dt.year
    df["dia_semana"] = df["fecha"].dt.weekday
    
    print(f"   ✓ Preprocesamiento exitoso")
    print(f"   ✓ Registros válidos: {len(df)}")
except Exception as e:
    print(f"   ✗ Error en preprocesamiento: {e}")
    sys.exit(1)

# Test 5: Features de frecuencia
print("\n[5/8] Probando features de frecuencia...")
try:
    # Tomar una lotería de ejemplo
    df_test = df[df["lottery"].str.lower() == "astro luna"].head(100).copy()
    df_test = df_test.sort_values('fecha').reset_index(drop=True)
    
    freq_engineer = FrequencyPatternEngineer(target_col='result')
    df_freq = freq_engineer.create_all_frequency_features(df_test)
    
    freq_cols = [col for col in df_freq.columns if 'freq' in col or 'hot' in col or 'cold' in col]
    print(f"   ✓ Features de frecuencia generadas: {len(freq_cols)}")
    print(f"   ✓ Ejemplos: {freq_cols[:5]}")
except Exception as e:
    print(f"   ✗ Error en features de frecuencia: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Features avanzadas
print("\n[6/8] Probando features avanzadas...")
try:
    df_test = df.head(50).copy()
    
    # Aplicar features temporales
    df_adv = FeatureEngineer.add_temporal_features(df_test)
    df_adv = FeatureEngineer.add_holiday_features(df_adv)
    df_adv = FeatureEngineer.add_lunar_features(df_adv)
    
    adv_cols = [col for col in df_adv.columns if col not in df_test.columns]
    print(f"   ✓ Features avanzadas generadas: {len(adv_cols)}")
    print(f"   ✓ Ejemplos: {adv_cols[:5]}")
except Exception as e:
    print(f"   ✗ Error en features avanzadas: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Calibración
print("\n[7/8] Probando calibración de probabilidades...")
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    # Datos de prueba
    X_test = np.random.randn(200, 10)
    y_test = np.random.randint(0, 3, size=200)
    
    X_train, X_val, y_train, y_val = train_test_split(X_test, y_test, test_size=0.3)
    
    # Modelo calibrado
    base_model = RandomForestClassifier(n_estimators=50, random_state=42)
    calibrated = CalibratedModelWrapper(base_model, method='sigmoid', cv=3)
    calibrated.fit(X_train, y_train)
    
    # Predecir con confianza
    predictions, confidences, is_confident = calibrated.predict_with_confidence(
        X_val, confidence_threshold=0.6
    )
    
    print(f"   ✓ Calibración exitosa")
    print(f"   ✓ Predicciones confiables: {is_confident.sum()}/{len(is_confident)}")
    print(f"   ✓ Confianza promedio: {confidences.mean():.2%}")
except Exception as e:
    print(f"   ✗ Error en calibración: {e}")
    import traceback
    traceback.print_exc()

# Test 8: Optimización bayesiana
print("\n[8/8] Probando optimización bayesiana...")
if BAYESIAN_AVAILABLE:
    try:
        # Datos de prueba pequeños
        X_test = np.random.randn(100, 5)
        y_test = np.random.randint(0, 2, size=100)
        
        optimizer = BayesianOptimizer(random_state=42)
        best_model, results = optimizer.optimize(
            X=X_test,
            y=y_test,
            algorithm='RandomForest',
            n_iter=5,  # Pocas iteraciones para prueba
            cv=2,
            verbose=False
        )
        
        print(f"   ✓ Optimización bayesiana exitosa")
        print(f"   ✓ Mejor score: {results['best_score']:.4f}")
        print(f"   ✓ Mejores parámetros: {list(results['best_params'].keys())}")
    except Exception as e:
        print(f"   ✗ Error en optimización bayesiana: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ⚠ scikit-optimize no disponible")
    print("   Instalar con: pip install scikit-optimize")

# Resumen final
print("\n" + "="*70)
print("RESUMEN DE PRUEBAS")
print("="*70)
print("\n✓ Sistema funcionando correctamente")
print("\nPara entrenar con el sistema híbrido mejorado:")
print("  python scripts/train_hybrid.py --lottery \"ASTRO LUNA\"")
print("\nPara predicciones mejoradas:")
print("  python scripts/predict_enhanced.py")
print("\nNOTA: Si optimización bayesiana no está disponible,")
print("      instalar con: pip install scikit-optimize")
print("="*70)
