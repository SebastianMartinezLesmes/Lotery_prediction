"""
Script para verificar información del modelo entrenado.
"""
import joblib
import os
from pathlib import Path

# Directorio de modelos
modelos_dir = Path("IA_models")

print("\n" + "="*70)
print("INFORMACIÓN DE MODELOS")
print("="*70)

# Buscar modelos .pkl
archivos_pkl = list(modelos_dir.glob("*.pkl"))

if not archivos_pkl:
    print("\n❌ No hay modelos .pkl en IA_models/")
else:
    print(f"\nModelos encontrados: {len(archivos_pkl)}\n")
    
    for archivo in archivos_pkl:
        print(f"\n{'='*70}")
        print(f"Archivo: {archivo.name}")
        print('='*70)
        
        try:
            modelo = joblib.load(archivo)
            
            # Información del modelo
            print(f"Tipo: {type(modelo).__name__}")
            
            if hasattr(modelo, 'n_features_in_'):
                print(f"Features: {modelo.n_features_in_}")
            else:
                print(f"Features: No disponible")
            
            if hasattr(modelo, 'n_estimators'):
                print(f"Estimadores: {modelo.n_estimators}")
            
            if hasattr(modelo, 'max_depth'):
                print(f"Max depth: {modelo.max_depth}")
            
            if hasattr(modelo, 'min_samples_split'):
                print(f"Min samples split: {modelo.min_samples_split}")
            
            if hasattr(modelo, 'class_weight'):
                print(f"Class weight: {modelo.class_weight}")
            
            # Tamaño del archivo
            size_mb = archivo.stat().st_size / (1024 * 1024)
            print(f"Tamaño: {size_mb:.2f} MB")
            
        except Exception as e:
            print(f"❌ Error al cargar: {e}")

print("\n" + "="*70)
print(f"Ubicación: {modelos_dir.absolute()}")
print("="*70)
