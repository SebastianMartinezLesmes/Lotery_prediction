Objetivo general

Migrar el proyecto para que PostgreSQL (Neon) sea la única fuente de datos.

El Excel dejará de utilizarse para entrenar o consultar información. Solo podrá existir como herramienta opcional para exportaciones o respaldo.

El flujo del proyecto será:

               Neon PostgreSQL
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
 Actualización    Entrenamiento   Predicción
      │              │              │
      ▼              ▼              ▼
 API Oficial      Modelos IA      Resultado
Arquitectura propuesta
src/

    api/
        API.py

    database/
        connection.py
        queries.py
        update_database.py
        schema.sql

    training/
        train.py

    prediction/
        predict.py

    models/
        astro_sol/
        astro_luna/

    utils/
Requerimiento 1
Actualización automática de la base de datos
Objetivo

Antes de realizar cualquier operación (entrenar o predecir), el sistema debe verificar si la base de datos está actualizada.

Flujo
Inicio

↓

Conectar a Neon

↓

Consultar la última fecha registrada

↓

última_fecha == ayer ?

        │

   Sí──────────────► Continuar

        │

        No

        │

fecha_inicio = última_fecha + 1

fecha_fin = ayer

↓

Consultar API Oficial

↓

Insertar registros nuevos

↓

Finalizar actualización
Reglas
Nunca descargar datos duplicados.
Nunca eliminar registros existentes.
Insertar únicamente sorteos faltantes.
Si un registro ya existe, actualizarlo únicamente si cambió.
Consulta SQL
SELECT MAX(fecha)
FROM resultados;
Requerimiento 2
Base de datos como única fuente de entrenamiento

Eliminar toda dependencia del Excel.

El entrenamiento debe realizar:

Neon

↓

SELECT *

↓

DataFrame

↓

Preprocesamiento

↓

Entrenamiento

↓

Guardar modelos

Consulta:

SELECT
    fecha,
    numero,
    signo,
    loteria
FROM resultados
ORDER BY fecha;
Salida esperada

Guardar los modelos entrenados en:

models/

    astro_sol/

        logistic.pkl
        tree.pkl

    astro_luna/

        logistic.pkl
        tree.pkl

Cada entrenamiento debe sobrescribir únicamente los modelos correspondientes.

Requerimiento 3
Predicción

Cuando el usuario solicite una predicción:

Conectar a Neon

↓

Obtener todos los datos históricos

↓

Cargar modelos entrenados

↓

Construir variables

↓

Realizar predicción

↓

Mostrar resultado

No volver a entrenar modelos durante una predicción.

Si no existen modelos entrenados:

Error:

"No existen modelos entrenados.
Ejecute primero el entrenamiento."
Requerimiento 4
Crear un servicio Database

Crear una clase encargada exclusivamente de PostgreSQL.

Ejemplo:

Database

connect()

disconnect()

get_last_date()

get_all_results()

insert_results()

update_result()

execute_query()

Todo el proyecto debe acceder a la base de datos únicamente mediante esta clase.

Requerimiento 5
Separar responsabilidades
api/

Responsabilidad:

Consumir API oficial.
Convertir respuesta a objetos Python.

No debe conocer PostgreSQL.

database/

Responsabilidad:

Conexión.
INSERT.
UPDATE.
SELECT.

No debe conocer modelos de IA.

training/

Responsabilidad:

Leer datos desde Neon.
Preparar DataFrame.
Entrenar modelos.
Guardarlos.

No debe consultar la API.

prediction/

Responsabilidad:

Leer datos desde Neon.
Cargar modelos.
Predecir.

No debe modificar la base de datos.

Requerimiento 6
Flujo principal del proyecto
Inicio

↓

Actualizar Base de Datos

↓

¿Usuario quiere entrenar?

      │

      Sí

      │

Entrenar modelos

      │

      No

↓

¿Usuario quiere predecir?

      │

      Sí

      │

Cargar modelos

↓

Predecir

↓

Fin
Requerimiento 7
GitHub Actions

El workflow debe ejecutarse tres veces por semana.

Su única responsabilidad será:

Conectar a Neon

↓

Verificar última fecha

↓

¿Hay datos faltantes?

      │

      Sí

↓

Consultar API

↓

Actualizar PostgreSQL

↓

Fin

El workflow no debe entrenar modelos ni generar predicciones, ya que estas tareas consumen más recursos y es preferible ejecutarlas bajo demanda o mediante un workflow independiente.

Requerimiento 8
Variables de entorno

Toda la configuración debe obtenerse desde variables de entorno.

Ejemplo:

DATABASE_URL=postgresql://...
API_URL=https://...
API_KEY=...
MODEL_PATH=models/

No deben existir credenciales escritas directamente en el código fuente.

Requerimiento 9
Registro de eventos (logging)

Registrar en un archivo de log:

Inicio de actualización.
Última fecha encontrada.
Fechas consultadas.
Número de registros descargados.
Registros insertados.
Registros actualizados.
Errores de conexión.
Inicio y fin del entrenamiento.
Inicio y fin de las predicciones.
Requerimiento 10
Prioridad de implementación
Configurar la conexión a Neon y definir el esquema de la base de datos.
Implementar el módulo database y las operaciones CRUD básicas.
Migrar los datos existentes del Excel a Neon (solo una vez).
Adaptar el módulo api para insertar y actualizar registros en Neon.
Implementar la lógica de sincronización basada en la última fecha registrada.
Modificar el entrenamiento para que lea exclusivamente desde Neon y guarde los modelos.
Modificar la predicción para que utilice los modelos entrenados y los datos almacenados en Neon.
Configurar un workflow de GitHub Actions dedicado únicamente a mantener sincronizada la base de datos.