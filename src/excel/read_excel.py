from openpyxl import load_workbook
from datetime import datetime, timedelta
import os
import subprocess
import sys  # ← importante para sys.executable

ARCHIVO = "resultados_astro.xlsx"
SCRIPT_ACTUALIZACION = ["-m", "src.excel.excel"]

def fecha_ayer():
    return (datetime.today() - timedelta(days=1)).date()

def obtener_ultima_fecha_excel():
    if not os.path.exists(ARCHIVO):
        print("📁 El archivo Excel no existe.")
        return None

    try:
        wb = load_workbook(ARCHIVO)  # ← sin read_only=True
        ws = wb.active

        fecha_col = None
        for col in ws.iter_cols(1, ws.max_column):
            if col[0].value and str(col[0].value).strip().lower() == "fecha":
                fecha_col = col
                break

        if not fecha_col:
            print("⚠️ No se encontró una columna llamada 'fecha'.")
            return None

        fechas = []
        for cell in fecha_col[1:]:  # Omitir encabezado
            try:
                if isinstance(cell.value, datetime):
                    fechas.append(cell.value.date())
                elif isinstance(cell.value, str):
                    fechas.append(datetime.strptime(cell.value, "%Y-%m-%d").date())
            except:
                continue

        if fechas:
            return max(fechas)
        else:
            return None
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return None

def ejecutar_actualizacion():
    print(f"⏳ Ejecutando actualización con {SCRIPT_ACTUALIZACION}...")
    subprocess.run([sys.executable] + SCRIPT_ACTUALIZACION, check=True)
    print("✅ Actualización completada.")

if __name__ == "__main__":
    ayer = fecha_ayer()
    ultima_fecha = obtener_ultima_fecha_excel()

    print(f"📅 Fecha de ayer: {ayer}")
    print(f"📄 Última fecha registrada: {ultima_fecha}")

    if ultima_fecha is None or ultima_fecha < ayer:
        print("🔄 Se necesita actualizar los resultados.")
        ejecutar_actualizacion()
    else:
        print("✅ Los resultados ya están actualizados.")
