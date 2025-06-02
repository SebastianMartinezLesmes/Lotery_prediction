import subprocess
import os

def ejecutar_script(nombre):
    print(f"\n🚀 Ejecutando: {nombre}")
    ruta = os.path.join(os.getcwd(), nombre)
    subprocess.run(["python", ruta], check=True)

if __name__ == "__main__":
    try:
        ejecutar_script("dependencias.py")
        ejecutar_script("API.py")
        ejecutar_script("ecxel.py")
        print("\n✅ Todos los scripts se ejecutaron correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al ejecutar un script: {e}")
