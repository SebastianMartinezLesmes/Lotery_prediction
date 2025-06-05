import os
import shutil
import stat

def onerror(func, path, exc_info):
    # Función para forzar eliminación incluso si está protegido
    try:
        os.chmod(path, stat.S_IWRITE)  # Forzar permisos de escritura
        func(path)
    except Exception as e:
        print(f"⚠️ Error forzado al eliminar {path}: {e}")

def eliminar_pycache(directorio_raiz="."):
    eliminadas = 0

    for dirpath, dirnames, _ in os.walk(directorio_raiz):
        if "__pycache__" in dirnames:
            ruta_completa = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(ruta_completa, onerror=onerror)
                print(f"🗑️ Eliminado: {ruta_completa}")
                eliminadas += 1
            except Exception as e:
                print(f"⚠️ Error al eliminar {ruta_completa}: {e}")

    if eliminadas == 0:
        print("✅ No se eliminaron carpetas '__pycache__'.")
    else:
        print(f"\n✅ Se eliminaron {eliminadas} carpetas '__pycache__'.")
