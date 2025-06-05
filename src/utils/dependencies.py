import os
import re
import subprocess
import sys
import importlib.util
import sysconfig

from src.utils.logger import configurar_logger

log = configurar_logger("DependenciasLogger", "dependencias.log")

def actualizar_pip():
    try:
        print("🔄 Actualizando pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("✅ pip actualizado correctamente.\n")
        log.info("pip actualizado correctamente.")
    except subprocess.CalledProcessError as e:
        print("❌ Error al actualizar pip.")
        log.error(f"Error al actualizar pip: {e}")

def obtener_archivos_py(base_path="."):
    archivos_py = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                ruta = os.path.join(root, file)
                if ruta != os.path.abspath(__file__):
                    archivos_py.append(ruta)
    return archivos_py

def extraer_dependencias(archivo):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
        patron = r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)'
        coincidencias = re.findall(patron, contenido, re.MULTILINE)
        modulos = list(set([mod.split('.')[0] for mod in coincidencias]))
        return modulos
    except Exception as e:
        log.warning(f"⚠️ No se pudo analizar {archivo}: {e}")
        return []

def esta_instalado(modulo):
    return importlib.util.find_spec(modulo) is not None

def es_modulo_estandar(modulo):
    try:
        ruta = importlib.util.find_spec(modulo).origin
        stdlib_path = sysconfig.get_paths()["stdlib"]
        return ruta.startswith(stdlib_path)
    except Exception:
        return False

def instalar(modulo):
    try:
        print(f"📦 Instalando módulo: {modulo}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", modulo])
        print(f"✅ {modulo} instalado correctamente.\n")
        log.info(f"Módulo instalado: {modulo}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al instalar {modulo}.")
        log.error(f"Error al instalar {modulo}: {e}")

def procesar_archivos():
    archivos_py = obtener_archivos_py()
    modulos_locales = [os.path.splitext(os.path.basename(f))[0] for f in archivos_py]

    total_dependencias = set()
    for archivo in archivos_py:
        print(f"\n🔍 Analizando: {archivo}")
        dependencias = extraer_dependencias(archivo)
        pendientes = []

        for dep in dependencias:
            if dep in modulos_locales:
                print(f"⏩ Módulo local ignorado: {dep}")
                continue
            if es_modulo_estandar(dep):
                print(f"✅ Módulo estándar: {dep}")
                continue
            if not esta_instalado(dep):
                print(f"🚫 Falta instalar: {dep}")
                pendientes.append(dep)
            else:
                print(f"✅ {dep} ya está instalado.")

        for dep in pendientes:
            instalar(dep)
            total_dependencias.add(dep)

        if not pendientes:
            print("📁 Todas las dependencias de este archivo están satisfechas.")
            log.info(f"{archivo} ✅ dependencias completas.")
        else:
            log.info(f"{archivo} 🔧 instaladas: {pendientes}")

    if total_dependencias:
        print(f"\n🎯 Dependencias nuevas instaladas: {', '.join(sorted(total_dependencias))}")
    else:
        print("\n✔️ No se encontraron nuevas dependencias por instalar.")

if __name__ == "__main__":
    actualizar_pip()
    procesar_archivos()