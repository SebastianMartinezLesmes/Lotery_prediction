import os
import re
import importlib.util
import sysconfig
import pkg_resources

def extraer_modulos_desde_archivos(base_path="."):
    modulos_detectados = set()

    for root, _, files in os.walk(base_path):
        for archivo in files:
            if archivo.endswith(".py"):
                ruta = os.path.join(root, archivo)
                try:
                    with open(ruta, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    patron = r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)'
                    coincidencias = re.findall(patron, contenido, re.MULTILINE)

                    for mod in coincidencias:
                        mod = mod.split('.')[0]
                        modulos_detectados.add(mod)

                except Exception as e:
                    print(f"⚠️ No se pudo leer {ruta}: {e}")

    return modulos_detectados

def es_modulo_estandar(modulo):
    try:
        ruta = importlib.util.find_spec(modulo).origin
        stdlib_path = sysconfig.get_paths()["stdlib"]
        return ruta and ruta.startswith(stdlib_path)
    except:
        return False

def generar_requirements_selectivo(nombre_archivo="requirements.txt", base_path="."):
    modulos_usados = extraer_modulos_desde_archivos(base_path)
    paquetes_instalados = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

    requerimientos = []

    for modulo in sorted(modulos_usados):
        if es_modulo_estandar(modulo):
            continue
        if modulo in paquetes_instalados:
            version = paquetes_instalados[modulo]
            requerimientos.append(f"{modulo}=={version}")
        else:
            print(f"⚠️ Módulo detectado pero no instalado: {modulo}")

    if requerimientos:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(requerimientos))
        print(f"\n✅ Archivo '{nombre_archivo}' generado con {len(requerimientos)} dependencias.")
    else:
        print("\nℹ️ No se encontraron módulos externos para registrar.")

if __name__ == "__main__":
    generar_requirements_selectivo()
