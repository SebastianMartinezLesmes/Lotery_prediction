# z_plan.md


# Plan detallado de implementación - Migración completa a Neon PostgreSQL

## Contexto
Este documento define qué debe implementar Kiro, en qué orden, qué archivos modificar, qué responsabilidades tendrá cada módulo y qué criterios debe cumplir.

## Objetivo general
Migrar completamente el proyecto para que Neon PostgreSQL sea la única fuente de datos.

La API oficial seguirá siendo la fuente de adquisición de información, pero toda lectura para entrenamiento y predicción deberá realizarse desde Neon.

## Estado actual
- Conexión con Neon implementada.
- Migración inicial del Excel a Neon completada.
- Pendiente: sincronización, entrenamiento y predicción usando Neon.

# Fase 1 - Base de datos como única fuente de verdad
- Eliminar toda dependencia de pandas.read_excel(), openpyxl y archivos Excel como origen de datos.
- Mantener el Excel únicamente para exportación si es necesario.

# Fase 2 - Capa de acceso a datos
Crear src/database con:
- connection.py
- repository.py
- queries.py

Responsabilidades:
- connect()
- close()
- get_last_date()
- get_all_results()
- get_results_between_dates()
- insert_results()
- update_result()

Ningún otro módulo debe ejecutar SQL.

# Fase 3 - Sincronización automática

Implementar synchronize_database():

1. Conectar a Neon.
2. Consultar MAX(fecha).
3. Calcular la fecha de ayer.
4. Si la última fecha == ayer, terminar.
5. En caso contrario:
   - fecha_inicio = última_fecha + 1 día
   - fecha_fin = ayer
6. Consultar la ruta oficial de Loterías usando el rango.
7. Insertar registros nuevos.
8. Actualizar registros existentes si cambiaron.
9. Registrar métricas en el log.

Debe ejecutarse antes del entrenamiento y antes de cada predicción.

# Fase 4 - Adaptar API
Mantener la lógica existente.
Solo aceptar fecha_inicio y fecha_fin y devolver objetos para persistencia.

# Fase 5 - Entrenamiento
Flujo:
Sincronizar -> Leer Neon -> DataFrame -> Preprocesar -> Entrenar -> Guardar modelos.

# Fase 6 - Predicción
Flujo:
Sincronizar -> Verificar modelos -> Leer Neon -> Construir variables -> Predecir.

Nunca entrenar durante la predicción.

# Fase 7 - GitHub Actions
Workflow:
- Ejecutar lunes, miércoles y viernes.
- Sincronizar Neon.
- Finalizar.
No entrenar ni predecir.

# Logging
Registrar:
- inicio/fin sincronización
- fechas consultadas
- registros insertados/actualizados
- errores
- inicio/fin entrenamiento
- inicio/fin predicción

# Criterios de aceptación
- Neon es la única fuente de datos.
- Excel no participa en entrenamiento ni predicción.
- Sincronización incremental.
- Sin duplicados.
- Entrenamiento y predicción leen únicamente desde Neon.
