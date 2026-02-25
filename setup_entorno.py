"""
Script de configuración inicial del entorno local.
Crea archivos y carpetas necesarias para el sistema.
"""
import os
import sys
from pathlib import Path
import shutil

def print_header(text):
    """Imprime un encabezado formateado."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_step(text, status="info"):
    """Imprime un paso con icono."""
    icons = {
        "info": "🔧",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }
    print(f"{icons.get(status, '•')} {text}")

def verificar_python():
    """Verifica la versión de Python."""
    print_step("Verificando versión de Python...", "info")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_step(f"Python {version.major}.{version.minor} detectado", "error")
        print_step("Se requiere Python 3.8 o superior", "error")
        return False
    
    print_step(f"Python {version.major}.{version.minor}.{version.micro} ✓", "success")
    return True

def crear_archivo_env():
    """Crea el archivo .env si no existe."""
    print_step("Configurando archivo .env...", "info")
    
    if Path(".env").exists():
        print_step("Archivo .env ya existe", "warning")
        respuesta = input("  ¿Deseas sobrescribirlo? (s/N): ").lower()
        if respuesta != 's':
            print_step("Manteniendo .env existente", "info")
            return True
    
    env_example = Path(".env.example")
    if not env_example.exists():
        print_step("No se encontró .env.example", "error")
        return False
    
    # Copiar .env.example a .env
    shutil.copy(env_example, ".env")
    print_step("Archivo .env creado desde .env.example", "success")
    return True

def crear_carpetas():
    """Crea las carpetas necesarias."""
    print_step("Creando estructura de carpetas...", "info")
    
    carpetas = [
        "IA_models",
        "data",
        "logs",
        "Docs"
    ]
    
    for carpeta in carpetas:
        path = Path(carpeta)
        if path.exists():
            print_step(f"  {carpeta}/ ya existe", "info")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print_step(f"  {carpeta}/ creada", "success")
        
        # Crear .gitkeep si no existe
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists() and carpeta in ["IA_models", "data", "logs"]:
            gitkeep.touch()
            print_step(f"  {carpeta}/.gitkeep creado", "success")
    
    return True

def verificar_dependencias():
    """Verifica si las dependencias están instaladas."""
    print_step("Verificando dependencias...", "info")
    
    dependencias_requeridas = [
        "pandas",
        "numpy",
        "scikit-learn",
        "openpyxl",
        "joblib",
        "requests",
        "tqdm",
        "python-dotenv",
        "pydantic"
    ]
    
    faltantes = []
    
    for dep in dependencias_requeridas:
        try:
            __import__(dep.replace("-", "_"))
            print_step(f"  {dep} ✓", "success")
        except ImportError:
            print_step(f"  {dep} ✗", "error")
            faltantes.append(dep)
    
    if faltantes:
        print_step(f"\nFaltan {len(faltantes)} dependencias", "warning")
        print("\nPara instalarlas, ejecuta:")
        print("  pip install -r requirements.txt")
        print("\nO instala manualmente:")
        print(f"  pip install {' '.join(faltantes)}")
        return False
    
    print_step("Todas las dependencias están instaladas", "success")
    return True

def verificar_archivos_clave():
    """Verifica que existan archivos clave del proyecto."""
    print_step("Verificando archivos clave...", "info")
    
    archivos = {
        "index.py": "Punto de entrada principal",
        "main.py": "CLI avanzado",
        "requirements.txt": "Lista de dependencias",
        "README.md": "Documentación principal",
        "src/core/config.py": "Configuración del sistema",
        "src/utils/training.py": "Entrenamiento de modelos",
        "src/utils/prediction.py": "Sistema de predicción"
    }
    
    todos_ok = True
    for archivo, descripcion in archivos.items():
        if Path(archivo).exists():
            print_step(f"  {archivo} ✓", "success")
        else:
            print_step(f"  {archivo} ✗ ({descripcion})", "error")
            todos_ok = False
    
    return todos_ok

def probar_configuracion():
    """Prueba que la configuración se cargue correctamente."""
    print_step("Probando configuración...", "info")
    
    try:
        from src.core.config import settings
        
        print_step(f"  API URL: {settings.API_URL}", "info")
        print_step(f"  Lotería: {settings.FIND_LOTERY}", "info")
        print_step(f"  Iteraciones: {settings.ITERATIONS}", "info")
        print_step(f"  Min Accuracy: {settings.MIN_ACCURACY}", "info")
        print_step(f"  Dir Modelos: {settings.MODELS_DIR}", "info")
        
        print_step("Configuración cargada correctamente", "success")
        return True
    
    except Exception as e:
        print_step(f"Error al cargar configuración: {e}", "error")
        return False

def mostrar_resumen():
    """Muestra un resumen del estado del entorno."""
    print_header("📊 RESUMEN DEL ENTORNO")
    
    checks = {
        "Python 3.8+": Path(sys.executable).exists(),
        "Archivo .env": Path(".env").exists(),
        "Carpeta IA_models": Path("IA_models").exists(),
        "Carpeta data": Path("data").exists(),
        "Carpeta logs": Path("logs").exists(),
        "requirements.txt": Path("requirements.txt").exists(),
        "index.py": Path("index.py").exists(),
        "main.py": Path("main.py").exists()
    }
    
    for item, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {item}")
    
    todos_ok = all(checks.values())
    
    print("\n" + "=" * 60)
    if todos_ok:
        print("🎉 Entorno configurado correctamente")
        print("\nPróximos pasos:")
        print("  1. Instalar dependencias: pip install -r requirements.txt")
        print("  2. Ejecutar el sistema: python index.py")
        print("  3. O usar CLI: python main.py --help")
    else:
        print("⚠️  Algunos componentes faltan")
        print("\nRevisa los errores arriba y corrígelos")
    print("=" * 60)

def main():
    """Función principal."""
    print_header("🚀 CONFIGURACIÓN DEL ENTORNO LOCAL")
    print("Sistema de Predicción de Lotería v2.0\n")
    
    pasos = [
        ("Verificar Python", verificar_python),
        ("Crear archivo .env", crear_archivo_env),
        ("Crear carpetas", crear_carpetas),
        ("Verificar archivos clave", verificar_archivos_clave),
        ("Verificar dependencias", verificar_dependencias),
        ("Probar configuración", probar_configuracion)
    ]
    
    resultados = []
    
    for nombre, funcion in pasos:
        print_header(nombre)
        try:
            resultado = funcion()
            resultados.append(resultado)
        except Exception as e:
            print_step(f"Error: {e}", "error")
            resultados.append(False)
    
    # Mostrar resumen
    mostrar_resumen()
    
    # Retornar código de salida
    return 0 if all(resultados) else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Configuración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error crítico: {e}")
        sys.exit(1)
