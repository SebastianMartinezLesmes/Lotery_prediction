"""
Módulo para limpiar archivos de cache de Python.
Elimina todas las carpetas __pycache__ del proyecto.
"""
import os
import stat
import shutil
from pathlib import Path


def onerror(func, path, exc_info):
    """
    Función para forzar eliminación incluso si está protegido.
    
    Args:
        func: Función que falló
        path: Ruta del archivo
        exc_info: Información de la excepción
    """
    try:
        os.chmod(path, stat.S_IWRITE)  # Forzar permisos de escritura
        func(path)
    except Exception as e:
        print(f"⚠️  Error forzado al eliminar {path}: {e}")


def eliminar_pycache(directorio_raiz="."):
    """
    Elimina todas las carpetas __pycache__ del proyecto.
    
    Args:
        directorio_raiz: Directorio desde donde empezar la búsqueda
    
    Returns:
        Número de carpetas eliminadas
    """
    eliminadas = 0
    directorio_raiz = Path(directorio_raiz).resolve()
    
    print(f"\nBuscando carpetas __pycache__ en: {directorio_raiz}")
    print("="*70)

    for dirpath, dirnames, _ in os.walk(directorio_raiz):
        if "__pycache__" in dirnames:
            ruta_completa = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(ruta_completa, onerror=onerror)
                print(f"✓ Eliminado: {ruta_completa}")
                eliminadas += 1
            except Exception as e:
                print(f"✗ Error al eliminar {ruta_completa}: {e}")

    print("="*70)
    if eliminadas == 0:
        print("✓ No se encontraron carpetas __pycache__ para eliminar.")
    else:
        print(f"✓ Se eliminaron {eliminadas} carpetas __pycache__.")
    
    return eliminadas


def eliminar_archivos_pyc(directorio_raiz="."):
    """
    Elimina todos los archivos .pyc del proyecto.
    
    Args:
        directorio_raiz: Directorio desde donde empezar la búsqueda
    
    Returns:
        Número de archivos eliminados
    """
    eliminados = 0
    directorio_raiz = Path(directorio_raiz).resolve()
    
    print(f"\nBuscando archivos .pyc en: {directorio_raiz}")
    print("="*70)

    for dirpath, _, filenames in os.walk(directorio_raiz):
        for filename in filenames:
            if filename.endswith('.pyc'):
                ruta_completa = os.path.join(dirpath, filename)
                try:
                    os.remove(ruta_completa)
                    print(f"✓ Eliminado: {ruta_completa}")
                    eliminados += 1
                except Exception as e:
                    print(f"✗ Error al eliminar {ruta_completa}: {e}")

    print("="*70)
    if eliminados == 0:
        print("✓ No se encontraron archivos .pyc para eliminar.")
    else:
        print(f"✓ Se eliminaron {eliminados} archivos .pyc.")
    
    return eliminados


def main():
    """
    Función principal para limpiar cache de Python.
    Elimina carpetas __pycache__ y archivos .pyc.
    """
    print("\n" + "="*70)
    print("LIMPIEZA DE CACHE DE PYTHON")
    print("="*70)
    
    # Obtener directorio raíz del proyecto
    directorio_raiz = Path(__file__).resolve().parent.parent.parent
    
    # Eliminar carpetas __pycache__
    carpetas_eliminadas = eliminar_pycache(directorio_raiz)
    
    # Eliminar archivos .pyc
    archivos_eliminados = eliminar_archivos_pyc(directorio_raiz)
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE LIMPIEZA")
    print("="*70)
    print(f"Carpetas __pycache__ eliminadas: {carpetas_eliminadas}")
    print(f"Archivos .pyc eliminados: {archivos_eliminados}")
    print(f"Total de elementos eliminados: {carpetas_eliminadas + archivos_eliminados}")
    print("="*70)
    
    return carpetas_eliminadas + archivos_eliminados


if __name__ == "__main__":
    main()