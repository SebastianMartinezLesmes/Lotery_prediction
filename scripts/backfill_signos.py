"""
Script para rellenar los signos zodiacales faltantes en el Excel.
Consulta SuperAstro para obtener los signos de las fechas que no los tienen.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime
import time

from src.api.superastro_scraper import SuperAstroScraper

# Ruta al Excel
excel_path = Path("data/resultados_astro.xlsx")

print("\n" + "="*70)
print("BACKFILL DE SIGNOS ZODIACALES")
print("="*70)

# Leer Excel
print(f"\nLeyendo: {excel_path}")
df = pd.read_excel(excel_path)

print(f"Total registros: {len(df)}")

# Contar registros sin signo
df['series'] = df['series'].astype(str)
sin_signo = df[df['series'].isin(['nan', 'NaN', ''])]

print(f"Registros sin signo: {len(sin_signo)}")

if len(sin_signo) == 0:
    print("\n✓ Todos los registros ya tienen signo zodiacal")
    exit(0)

# Crear scraper
scraper = SuperAstroScraper(delay_entre_requests=1.5)

print(f"\nObteniendo signos desde SuperAstro...")
print("="*70)

# Procesar cada registro sin signo
actualizados = 0
errores = 0

for idx, row in sin_signo.iterrows():
    fecha = pd.to_datetime(row['fecha'])
    loteria = row['lottery']
    
    print(f"\n{actualizados + errores + 1}/{len(sin_signo)} - {fecha.strftime('%Y-%m-%d')} - {loteria}")
    
    try:
        # Obtener resultado desde SuperAstro
        resultado = scraper.obtener_resultados_fecha(fecha, loteria)
        
        if resultado and resultado.get('series'):
            # Actualizar el DataFrame
            df.at[idx, 'series'] = resultado['series']
            print(f"  ✓ Signo encontrado: {resultado['series']}")
            actualizados += 1
        else:
            print(f"  ✗ No se encontró signo")
            errores += 1
        
        # Pausa entre requests
        time.sleep(1.5)
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        errores += 1

print("\n" + "="*70)
print("RESUMEN")
print("="*70)
print(f"Actualizados: {actualizados}")
print(f"Errores: {errores}")
print("="*70)

if actualizados > 0:
    # Guardar Excel actualizado
    print(f"\nGuardando Excel actualizado...")
    df.to_excel(excel_path, index=False)
    print(f"✓ Excel guardado exitosamente")
    
    # Mostrar últimos 5 registros
    print("\nÚltimos 5 registros:")
    print(df.tail(5).to_string(index=False))
else:
    print("\n⚠️  No se actualizó ningún registro")

print("="*70)
