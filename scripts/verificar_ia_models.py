"""
Script de verificación para confirmar que el cambio models → IA_models fue exitoso.
"""
import os
import sys
from pathlib import Path

def verificar_estructura():
    """Verifica que la estructura de carpetas sea correcta."""
    print("🔍 Verificando estructura de carpetas...\n")
    
    checks = []
    
    # 1. Verificar que IA_models existe
    ia_models_exists = Path("IA_models").exists()
    checks.append(("IA_models/ existe", ia_models_exists))
    
    # 2. Verificar que models NO existe
    models_not_exists = not Path("models").exists()
    checks.append(("models/ NO existe (correcto)", models_not_exists))
    
    # 3. Verificar que src/models existe (esquemas Pydantic)
    src_models_exists = Path("src/models").exists()
    checks.append(("src/models/ existe (esquemas)", src_models_exists))
    
    # 4. Verificar .gitkeep en IA_models
    gitkeep_exists = Path("IA_models/.gitkeep").exists()
    checks.append(("IA_models/.gitkeep existe", gitkeep_exists))
    
    # 5. Contar modelos .pkl en IA_models
    if ia_models_exists:
        pkl_files = list(Path("IA_models").glob("*.pkl"))
        pkl_count = len(pkl_files)
        checks.append((f"Modelos .pkl encontrados: {pkl_count}", pkl_count >= 0))
    
    # Mostrar resultados
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


def verificar_configuracion():
    """Verifica que la configuración apunte a IA_models."""
    print("\n🔍 Verificando configuración...\n")
    
    try:
        from src.core.config import settings
        
        checks = []
        
        # Verificar que MODELS_DIR apunta a IA_models
        models_dir_correct = "IA_models" in str(settings.MODELS_DIR)
        checks.append((f"settings.MODELS_DIR = {settings.MODELS_DIR}", models_dir_correct))
        
        # Verificar que el directorio existe
        dir_exists = settings.MODELS_DIR.exists()
        checks.append(("Directorio existe", dir_exists))
        
        # Verificar método get_model_path
        test_path = settings.get_model_path("test_lottery", "result")
        path_correct = "IA_models" in str(test_path)
        checks.append((f"get_model_path() usa IA_models", path_correct))
        
        # Mostrar resultados
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    except Exception as e:
        print(f"❌ Error al verificar configuración: {e}")
        return False


def verificar_config_legacy():
    """Verifica configuración legacy en src/utils/config.py."""
    print("\n🔍 Verificando configuración legacy...\n")
    
    try:
        # Nota: src/utils/config.py es legacy, pero verificamos por compatibilidad
        try:
            from src.utils.config import CARPETA_MODELOS, MODELO_RESULT_PATH, MODELO_SERIES_PATH
        except ImportError:
            print("⚠️  src/utils/config.py no encontrado (ya fue migrado)")
            return True
        
        checks = []
        
        # Verificar CARPETA_MODELOS
        carpeta_correct = CARPETA_MODELOS == "IA_models"
        checks.append((f"CARPETA_MODELOS = '{CARPETA_MODELOS}'", carpeta_correct))
        
        # Verificar rutas de modelos
        result_correct = "IA_models" in MODELO_RESULT_PATH
        checks.append((f"MODELO_RESULT_PATH usa IA_models", result_correct))
        
        series_correct = "IA_models" in MODELO_SERIES_PATH
        checks.append((f"MODELO_SERIES_PATH usa IA_models", series_correct))
        
        # Mostrar resultados
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_passed = False
        
        return all_passed
    
    except Exception as e:
        print(f"❌ Error al verificar config legacy: {e}")
        return False


def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 60)
    print("🔧 VERIFICACIÓN: Cambio models → IA_models")
    print("=" * 60)
    print()
    
    resultados = []
    
    # Verificar estructura
    resultados.append(verificar_estructura())
    
    # Verificar configuración
    resultados.append(verificar_configuracion())
    
    # Verificar config legacy
    resultados.append(verificar_config_legacy())
    
    # Resumen final
    print("\n" + "=" * 60)
    if all(resultados):
        print("🎉 TODAS LAS VERIFICACIONES PASARON")
        print("=" * 60)
        print("\n✅ El cambio a IA_models fue exitoso")
        print("✅ El sistema está listo para usar")
        return 0
    else:
        print("⚠️  ALGUNAS VERIFICACIONES FALLARON")
        print("=" * 60)
        print("\n❌ Revisa los errores arriba")
        print("❌ Consulta CAMBIOS_IA_MODELS.md para más información")
        return 1


if __name__ == "__main__":
    sys.exit(main())
