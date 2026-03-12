"""
Script para limpiar el Excel y dejar solo las 4 columnas esenciales.
También convierte los signos zodiacales a abreviaciones de 3 letras.
"""
import pandas as pd
from pathlib import Path

# Mapeo de signos a abreviaciones
SIGNOS_ABREV = {
    'ARIES': 'ARI',
    'TAURO': 'TAU',
    'GEMINIS': 'GEM',
    'GÉMINIS': 'GEM',
    'CANCER': 'CAN',
    'CÁNCER': 'CAN',
    'LEO': 'LEO',
    'VIRGO': 'VIR',
    'LIBRA': 'LIB',
    'ESCORPIO': 'ESC',
    'ESCORPION': 'ESC',
    'SAGITARIO': 'SAG',
    'CAPRICORNIO': 'CAP',
    'ACUARIO': 'ACU',
    'PISCIS': 'PIS'
}

# Ruta al Excel
excel_path = Path("data/resultados_astro.xlsx")

print("\n" + "="*70)
print("LIMPIEZA DE EXCEL")
print("="*70)

# Leer Excel
print(f"\nLeyendo: {excel_path}")
df = pd.read_excel(excel_path)

print(f"Columnas actuales: {list(df.columns)}")
print(f"Total registros: {len(df)}")

# Seleccionar solo las 4 columnas esenciales
columnas_necesarias = ['fecha', 'lottery', 'result', 'series']

# Verificar que existan
columnas_faltantes = [col for col in columnas_necesarias if col not in df.columns]
if columnas_faltantes:
    print(f"\n❌ Error: Faltan columnas: {columnas_faltantes}")
    exit(1)

# Crear DataFrame limpio
df_limpio = df[columnas_necesarias].copy()

# Convertir signos a abreviaciones de 3 letras
print(f"\nConvirtiendo signos a abreviaciones...")
df_limpio['series'] = df_limpio['series'].str.upper().map(SIGNOS_ABREV)

# Verificar si hay signos no mapeados
signos_no_mapeados = df_limpio[df_limpio['series'].isna()]['series'].unique()
if len(signos_no_mapeados) > 0:
    print(f"⚠️  Advertencia: Signos no mapeados encontrados: {signos_no_mapeados}")

# Guardar
print(f"\nGuardando Excel limpio...")
df_limpio.to_excel(excel_path, index=False)

print(f"\n✓ Excel limpiado exitosamente")
print(f"Columnas finales: {list(df_limpio.columns)}")
print(f"Total registros: {len(df_limpio)}")
print("="*70)

# Mostrar últimos 5 registros
print("\nÚltimos 5 registros:")
print(df_limpio.tail(5).to_string(index=False))
print("="*70)

# Mostrar signos únicos
print("\nSignos únicos en el Excel:")
print(sorted(df_limpio['series'].unique()))
print("="*70)
