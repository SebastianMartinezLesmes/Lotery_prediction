import subprocess
import sys
from src.utils.logger import configurar_logger
from src.utils.drop_cache import eliminar_pycache

log = configurar_logger()

# Scripts por orden de ejecución
scripts = [
    ("Dependencias", "src/utils/dependencies.py"),
    ("Recolección de Datos", "src/excel/read_excel.py"),
    ("Predicción", "src/utils/prediction.py")
]

def ejecutar_script(nombre_amigable, ruta_script):
    log.info(f"▶ Ejecutando: {nombre_amigable} ({ruta_script})")
    print(f"🔧 {nombre_amigable}...")
    try:
        modulo = ruta_script.replace("/", ".").replace(".py", "")
        subprocess.run([sys.executable, "-m", modulo], check=True)
        log.info(f"✅ Completado: {nombre_amigable}")
        print(f"✅ {nombre_amigable} completado.\n")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"❌ Falló: {nombre_amigable} - {e}")
        print(f"❌ Error en {nombre_amigable}. Detalles en el log.\n")
        return False

if __name__ == "__main__":
    print("🎯 INICIO DE EJECUCIÓN DEL SISTEMA DE LOTERÍA\n" + "-"*45)

    total = len(scripts)
    correctos = 0

    for nombre, ruta in scripts:
        if ejecutar_script(nombre, ruta):
            correctos += 1
        else:
            break  # Detener si falla

    print("🧾 RESUMEN FINAL")
    print("-" * 45)
    print(f"✔️ Scripts exitosos: {correctos}/{total}")
    print(f"📂 Registro detallado: logs/log_loteria.log")
    print("-" * 45)

    log.info(f"🎯 Proceso completo: {correctos}/{total} scripts ejecutados.")

    print("\n🧹 Limpiando cachés (__pycache__)...\n")
    eliminar_pycache()
