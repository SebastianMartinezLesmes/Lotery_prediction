"""
Migración de datos desde Excel a Neon PostgreSQL.

Uso:
    python scripts/migrar_a_neon.py

Requiere:
    pip install psycopg2-binary
"""
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")
EXCEL_PATH   = Path("data/resultados_astro.xlsx")

if not DATABASE_URL:
    print("❌ DATABASE_URL no encontrada en .env")
    sys.exit(1)

if not EXCEL_PATH.exists():
    print(f"❌ Excel no encontrado: {EXCEL_PATH}")
    sys.exit(1)


# ============================================================
# LEER EXCEL
# ============================================================

print("\n" + "="*60)
print("MIGRACIÓN EXCEL → NEON POSTGRESQL")
print("="*60)

print(f"\n📂 Leyendo: {EXCEL_PATH}")
df = pd.read_excel(EXCEL_PATH)
df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
df = df.dropna(subset=["fecha", "lottery", "result", "series"])
df["result"] = df["result"].astype(int)
df["series"] = df["series"].astype(str).str.upper().str.strip()

print(f"   Registros encontrados: {len(df)}")
print(f"   Loterías: {sorted(df['lottery'].unique())}")
print(f"   Signos únicos: {sorted(df['series'].unique())}")
print(f"   Rango de fechas: {df['fecha'].min()} → {df['fecha'].max()}")


# ============================================================
# CONECTAR A NEON
# ============================================================

print(f"\n🔌 Conectando a Neon...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    print("   ✅ Conexión exitosa")
except Exception as e:
    print(f"   ❌ Error de conexión: {e}")
    sys.exit(1)


# ============================================================
# CREAR ESQUEMA SI NO EXISTE
# ============================================================

print("\n🏗  Creando esquema (si no existe)...")

cur.execute("""
    CREATE TABLE IF NOT EXISTS loterias (
        id     SERIAL PRIMARY KEY,
        nombre VARCHAR(50) NOT NULL UNIQUE
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS signos (
        id     SERIAL PRIMARY KEY,
        codigo CHAR(3)     NOT NULL UNIQUE,
        nombre VARCHAR(20) NOT NULL
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id         SERIAL PRIMARY KEY,
        fecha      DATE     NOT NULL,
        loteria_id INT      NOT NULL REFERENCES loterias(id),
        result     SMALLINT NOT NULL CHECK (result BETWEEN 0 AND 9999),
        signo_id   INT      NOT NULL REFERENCES signos(id),
        UNIQUE (fecha, loteria_id)
    );
""")

cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_resultados_fecha
        ON resultados(fecha DESC);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_resultados_loteria
        ON resultados(loteria_id);
""")

# Vista para consultas fáciles (equivalente al Excel)
cur.execute("""
    CREATE OR REPLACE VIEW v_resultados AS
    SELECT
        r.fecha,
        l.nombre  AS lottery,
        r.result,
        s.codigo  AS series
    FROM resultados r
    JOIN loterias l ON l.id = r.loteria_id
    JOIN signos   s ON s.id = r.signo_id
    ORDER BY r.fecha DESC;
""")

conn.commit()
print("   ✅ Esquema listo")


# ============================================================
# INSERTAR LOTERÍAS
# ============================================================

loterias_excel = df["lottery"].unique()
for nombre in loterias_excel:
    cur.execute("""
        INSERT INTO loterias (nombre)
        VALUES (%s)
        ON CONFLICT (nombre) DO NOTHING;
    """, (nombre,))

# Cargar mapa nombre → id
cur.execute("SELECT nombre, id FROM loterias;")
loteria_map = {row[0]: row[1] for row in cur.fetchall()}
conn.commit()


# ============================================================
# INSERTAR SIGNOS
# ============================================================

SIGNOS_NOMBRES = {
    "ARI": "Aries",    "TAU": "Tauro",    "GEM": "Géminis",
    "CAN": "Cáncer",   "LEO": "Leo",      "VIR": "Virgo",
    "LIB": "Libra",    "ESC": "Escorpio", "SAG": "Sagitario",
    "CAP": "Capricornio", "ACU": "Acuario", "PIS": "Piscis"
}

for codigo, nombre in SIGNOS_NOMBRES.items():
    cur.execute("""
        INSERT INTO signos (codigo, nombre)
        VALUES (%s, %s)
        ON CONFLICT (codigo) DO NOTHING;
    """, (codigo, nombre))

# Cargar mapa codigo → id
cur.execute("SELECT codigo, id FROM signos;")
signo_map = {row[0]: row[1] for row in cur.fetchall()}
conn.commit()


# ============================================================
# MIGRAR RESULTADOS
# ============================================================

print(f"\n📤 Migrando {len(df)} registros...")

filas_ok      = 0
filas_skip    = 0
filas_error   = 0
signos_desconocidos = set()

rows = []
for _, row in df.iterrows():
    loteria_id = loteria_map.get(row["lottery"])
    signo_id   = signo_map.get(row["series"])

    if loteria_id is None:
        filas_error += 1
        continue

    if signo_id is None:
        signos_desconocidos.add(row["series"])
        filas_error += 1
        continue

    rows.append((row["fecha"], loteria_id, int(row["result"]), signo_id))

# Insertar en lote (ignorar duplicados por UNIQUE fecha+loteria)
if rows:
    try:
        execute_values(cur, """
            INSERT INTO resultados (fecha, loteria_id, result, signo_id)
            VALUES %s
            ON CONFLICT (fecha, loteria_id) DO NOTHING
            RETURNING id;
        """, rows)
        inserted = cur.rowcount
        filas_ok   = inserted if inserted > 0 else 0
        filas_skip = len(rows) - filas_ok
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"   ❌ Error en inserción masiva: {e}")
        sys.exit(1)


# ============================================================
# RESUMEN FINAL
# ============================================================

cur.execute("SELECT COUNT(*) FROM resultados;")
total_db = cur.fetchone()[0]

print("\n" + "="*60)
print("RESUMEN DE MIGRACIÓN")
print("="*60)
print(f"  Registros en Excel  : {len(df)}")
print(f"  Insertados nuevos   : {filas_ok}")
print(f"  Duplicados omitidos : {filas_skip}")
print(f"  Errores             : {filas_error}")
print(f"  Total en Neon ahora : {total_db}")

if signos_desconocidos:
    print(f"\n  ⚠️  Signos no reconocidos: {signos_desconocidos}")
    print("     Agrégalos a SIGNOS_NOMBRES en este script.")

print("\n  ✅ Migración completada")
print("="*60)

# Mostrar últimos 5 registros como verificación
cur.execute("SELECT fecha, lottery, result, series FROM v_resultados LIMIT 5;")
rows_preview = cur.fetchall()
print("\nPrimeros 5 registros en Neon:")
print(f"  {'FECHA':<12} {'LOTERÍA':<12} {'RESULT':<8} {'SIGNO'}")
print(f"  {'-'*45}")
for r in rows_preview:
    print(f"  {str(r[0]):<12} {r[1]:<12} {r[2]:<8} {r[3]}")

cur.close()
conn.close()
