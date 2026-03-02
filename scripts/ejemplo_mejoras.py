"""
Script de Ejemplo: Uso de las Mejoras de ML

Demuestra cómo usar las tres mejoras implementadas:
1. Features de frecuencia y patrones
2. Calibración de probabilidades
3. Optimización bayesiana

Uso:
    python scripts/ejemplo_mejoras.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

from src.utils.ml_enhanced import (
    FrequencyPatternEngineer,
    CalibratedModelWrapper,
    BayesianOptimizer,
    BAYESIAN_AVAILABLE
)


def ejemplo_1_features_frecuencia():
    """Ejemplo 1: Features de Frecuencia y Patrones"""
    print("\n" + "="*70)
    print("EJEMPLO 1: FEATURES DE FRECUENCIA Y PATRONES")
    print("="*70)
    
    # Crear datos de ejemplo
    print("\nCreando datos de ejemplo...")
    fechas = pd.date_range('2024-01-01', periods=200, freq='D')
    numeros = np.random.randint(0, 100, size=200)
    
    df = pd.DataFrame({
        'fecha': fechas,
        'result': numeros
    })
    
    print(f"Datos originales: {df.shape[1]} columnas")
    print(f"Columnas: {list(df.columns)}")
    
    # Crear ingeniero de features
    print("\nGenerando features de frecuencia...")
    freq_engineer = FrequencyPatternEngineer(target_col='result')
    
    # Generar todas las features
    df_enhanced = freq_engineer.create_all_frequency_features(df)
    
    print(f"\nDatos mejorados: {df_enhanced.shape[1]} columnas")
    print(f"Features agregadas: {df_enhanced.shape[1] - df.shape[1]}")
    
    # Mostrar algunas features
    print("\nEjemplos de features generadas:")
    feature_cols = [col for col in df_enhanced.columns if col not in ['fecha', 'result']]
    for col in feature_cols[:10]:
        print(f"   - {col}")
    
    if len(feature_cols) > 10:
        print(f"   ... y {len(feature_cols) - 10} más")
    
    # Mostrar ejemplo de número caliente
    hot_numbers = df_enhanced[df_enhanced['result_is_hot'] == 1]['result'].unique()
    if len(hot_numbers) > 0:
        print(f"\nNúmeros calientes detectados: {hot_numbers[:5]}")
    
    print("\n✅ Ejemplo 1 completado")


def ejemplo_2_calibracion():
    """Ejemplo 2: Calibración de Probabilidades"""
    print("\n" + "="*70)
    print("EJEMPLO 2: CALIBRACIÓN DE PROBABILIDADES")
    print("="*70)
    
    # Crear datos de ejemplo
    print("\nCreando datos de ejemplo...")
    np.random.seed(42)
    X = np.random.randn(1000, 10)
    y = np.random.randint(0, 5, size=1000)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    
    print(f"Datos de entrenamiento: {X_train.shape}")
    print(f"Datos de prueba: {X_test.shape}")
    
    # Entrenar modelo sin calibrar
    print("\nEntrenando modelo sin calibrar...")
    model_base = RandomForestClassifier(n_estimators=100, random_state=42)
    model_base.fit(X_train, y_train)
    
    # Evaluar sin calibrar
    y_pred_base = model_base.predict(X_test)
    acc_base = accuracy_score(y_test, y_pred_base)
    
    print(f"Accuracy sin calibrar: {acc_base:.4f}")
    
    # Entrenar modelo calibrado
    print("\nEntrenando modelo con calibración...")
    calibrated_model = CalibratedModelWrapper(
        base_model=RandomForestClassifier(n_estimators=100, random_state=42),
        method='sigmoid',
        cv=5
    )
    calibrated_model.fit(X_train, y_train)
    
    # Evaluar con calibración
    y_pred_cal = calibrated_model.predict(X_test)
    acc_cal = accuracy_score(y_test, y_pred_cal)
    
    print(f"Accuracy con calibración: {acc_cal:.4f}")
    
    # Predecir con umbral de confianza
    print("\nPredicciones con umbral de confianza (60%)...")
    predictions, confidences, is_confident = calibrated_model.predict_with_confidence(
        X_test,
        confidence_threshold=0.6
    )
    
    confident_pct = (is_confident.sum() / len(is_confident)) * 100
    
    print(f"Predicciones totales: {len(predictions)}")
    print(f"Predicciones confiables: {is_confident.sum()} ({confident_pct:.1f}%)")
    print(f"Confianza promedio: {confidences.mean():.2%}")
    print(f"Confianza mínima: {confidences.min():.2%}")
    print(f"Confianza máxima: {confidences.max():.2%}")
    
    # Accuracy solo en predicciones confiables
    if is_confident.sum() > 0:
        acc_confident = accuracy_score(
            y_test[is_confident],
            predictions[is_confident]
        )
        print(f"\nAccuracy en predicciones confiables: {acc_confident:.4f}")
        print(f"Mejora: {(acc_confident - acc_base) * 100:.1f} puntos porcentuales")
    
    print("\n✅ Ejemplo 2 completado")


def ejemplo_3_optimizacion_bayesiana():
    """Ejemplo 3: Optimización Bayesiana"""
    print("\n" + "="*70)
    print("EJEMPLO 3: OPTIMIZACIÓN BAYESIANA")
    print("="*70)
    
    if not BAYESIAN_AVAILABLE:
        print("\n⚠️  scikit-optimize no está instalado")
        print("Instalar con: pip install scikit-optimize")
        return
    
    # Crear datos de ejemplo
    print("\nCreando datos de ejemplo...")
    np.random.seed(42)
    X = np.random.randn(500, 15)
    y = np.random.randint(0, 3, size=500)
    
    print(f"Datos: {X.shape}")
    print(f"Clases: {np.unique(y)}")
    
    # Optimización bayesiana
    print("\nOptimizando hiperparámetros con búsqueda bayesiana...")
    print("(Esto puede tomar 1-2 minutos)")
    
    optimizer = BayesianOptimizer(random_state=42)
    
    best_model, results = optimizer.optimize(
        X=X,
        y=y,
        algorithm='RandomForest',
        n_iter=20,  # Pocas iteraciones para el ejemplo
        cv=3,
        verbose=True
    )
    
    print(f"\n✅ Optimización completada")
    print(f"Mejor score: {results['best_score']:.4f}")
    print(f"\nMejores hiperparámetros encontrados:")
    for param, value in results['best_params'].items():
        print(f"   {param}: {value}")
    
    print("\n✅ Ejemplo 3 completado")


def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "="*70)
    print("EJEMPLOS DE USO DE MEJORAS DE ML")
    print("="*70)
    print("\nEste script demuestra las tres mejoras implementadas:")
    print("1. Features de frecuencia y patrones")
    print("2. Calibración de probabilidades")
    print("3. Optimización bayesiana")
    
    # Ejecutar ejemplos
    ejemplo_1_features_frecuencia()
    ejemplo_2_calibracion()
    ejemplo_3_optimizacion_bayesiana()
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print("\n✅ Todos los ejemplos completados")
    print("\nPara usar estas mejoras en producción:")
    print("   1. Entrenar: python scripts/train_enhanced.py")
    print("   2. Predecir: python scripts/predict_enhanced.py")
    print("\nVer documentación completa en: Docs/MEJORAS_ML.md")


if __name__ == "__main__":
    main()
