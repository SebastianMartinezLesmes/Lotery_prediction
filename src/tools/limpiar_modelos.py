"""
Script para eliminar modelos antiguos y permitir re-entrenamiento.
"""
import os
from pathlib import Path

# Directorio de modelos
modelos_dir = Path("IA_models")

print("\n" + "="*70)
print("LIMPIEZA DE MODELOS")
print("="*70)

# Buscar archivos .pkl
archivos_pkl = list(modelos_dir.glob("*.pkl"))

if not archivos_pkl:
    print("\n✓ No hay modelos .pkl para eliminar")
else:
    print(f"\nModelos encontrados: {len(archivos_pkl)}")
    
    for archivo in archivos_pkl:
        print(f"\n  Eliminando: {archivo.name}")
        try:
            archivo.unlink()
            print(f"  ✓ Eliminado")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Se eliminaron {len(archivos_pkl)} modelos")

# Buscar archivos .json de variantes híbridas
archivos_json = list(modelos_dir.glob("hybrid_variants_*.json"))

if archivos_json:
    print(f"\nVariantes híbridas encontradas: {len(archivos_json)}")
    
    for archivo in archivos_json:
        print(f"\n  Eliminando: {archivo.name}")
        try:
            archivo.unlink()
            print(f"  ✓ Eliminado")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Se eliminaron {len(archivos_json)} archivos de variantes")

print("\n" + "="*70)
print("LIMPIEZA COMPLETADA")
print("="*70)
print("\nAhora puedes entrenar nuevos modelos con:")
print("  python main.py --entrenar")
print("="*70)
