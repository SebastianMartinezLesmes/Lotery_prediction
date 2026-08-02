"""
Consultas SQL para la base de datos Neon PostgreSQL.

Schema en Neon:
  - loterias(id, nombre)
  - signos(id, codigo, nombre)
  - resultados(id, fecha, loteria_id, result, signo_id)
  - vista: v_resultados(fecha, lottery, result, series)
"""

# Obtener la última fecha registrada para una lotería
GET_LAST_DATE = """
    SELECT MAX(fecha) AS last_date
    FROM v_resultados
    WHERE UPPER(lottery) = UPPER(%(loteria)s)
"""

# Obtener todos los resultados de una lotería
GET_ALL_RESULTS = """
    SELECT fecha, lottery, result, series
    FROM v_resultados
    WHERE UPPER(lottery) = UPPER(%(loteria)s)
    ORDER BY fecha ASC
"""

# Obtener resultados entre dos fechas para una lotería
GET_RESULTS_BETWEEN = """
    SELECT fecha, lottery, result, series
    FROM v_resultados
    WHERE UPPER(lottery) = UPPER(%(loteria)s)
      AND fecha BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
    ORDER BY fecha ASC
"""

# Obtener el ID de una lotería por nombre
GET_LOTERIA_ID = """
    SELECT id FROM loterias WHERE UPPER(nombre) = UPPER(%(loteria)s)
"""

# Obtener el ID de un signo por código
GET_SIGNO_ID = """
    SELECT id FROM signos WHERE UPPER(codigo) = UPPER(%(series)s)
"""

# Insertar un resultado nuevo (falla silenciosamente si ya existe)
INSERT_RESULT = """
    INSERT INTO resultados (fecha, loteria_id, result, signo_id)
    VALUES (
        %(fecha)s,
        (SELECT id FROM loterias WHERE UPPER(nombre) = UPPER(%(loteria)s)),
        %(result)s,
        (SELECT id FROM signos  WHERE UPPER(codigo)  = UPPER(%(series)s))
    )
    ON CONFLICT (fecha, loteria_id) DO NOTHING
"""

# Insertar o actualizar si ya existe (ON CONFLICT sobre fecha + loteria_id)
UPSERT_RESULT = """
    INSERT INTO resultados (fecha, loteria_id, result, signo_id)
    VALUES (
        %(fecha)s,
        (SELECT id FROM loterias WHERE UPPER(nombre) = UPPER(%(loteria)s)),
        %(result)s,
        (SELECT id FROM signos  WHERE UPPER(codigo)  = UPPER(%(series)s))
    )
    ON CONFLICT (fecha, loteria_id)
    DO UPDATE SET
        result   = EXCLUDED.result,
        signo_id = EXCLUDED.signo_id
"""

# Actualizar un resultado existente por fecha y lotería
UPDATE_RESULT = UPSERT_RESULT
