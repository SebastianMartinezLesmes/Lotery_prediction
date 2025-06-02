import os
import re
import subprocess
import sys
import importlib.util
import sysconfig

def extraer_dependencias(archivo):
    with open(archivo, "r", encoding="utf-8") as f:
        contenido = f.read()

    patron = r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)'
    coincidencias = re.findall(patron, contenido, re.MULTILINE)
    modulos = list(set([mod.split('.')[0] for mod in coincidencias]))
    return modulos

def esta_instalado(modulo):
    return importlib.util.find_spec(modulo) is not None

def es_modulo_estandar(modulo):
    """Verifica si el módulo es parte de la librería estándar de Python."""
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
    except subprocess.CalledProcessError:
        print(f"❌ Error al instalar {modulo}.\n")

def procesar_archivos():
    archivos_py = [f for f in os.listdir() if f.endswith(".py") and f != os.path.basename(__file__)]
    modulos_locales = [os.path.splitext(f)[0] for f in archivos_py]

    for archivo in archivos_py:
        print(f"\n🔍 Analizando dependencias en: {archivo}")
        dependencias = extraer_dependencias(archivo)
        pendientes = []

        for dep in dependencias:
            if dep in modulos_locales:
                print(f"⏩ Ignorando módulo local: {dep}")
                continue
            if es_modulo_estandar(dep):
                print(f"✅ Módulo estándar detectado: {dep}")
                continue
            if not esta_instalado(dep):
                print(f"🚫 Dependencia no instalada: {dep}")
                pendientes.append(dep)
            else:
                print(f"✅ {dep} ya está instalada.")

        if pendientes:
            print(f"\n🛠 Instalando dependencias faltantes para {archivo}...")
            for dep in pendientes:
                instalar(dep)
        else:
            print(f"📁 Todas las dependencias de {archivo} están satisfechas.")

if __name__ == "__main__":
    procesar_archivos()
