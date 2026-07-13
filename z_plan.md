# Plan de Refactorización del Proyecto

## Objetivo General

Realizar una limpieza del proyecto para mejorar su arquitectura, reducir código innecesario y preparar el entorno para una ejecución completamente automatizada.

Este documento describe las tareas que deben implementarse, el orden recomendado y los criterios de aceptación para cada una.

---

# Objetivo 1 - Centralizar la configuración y las credenciales

## Descripción

Actualmente existen configuraciones, credenciales y constantes distribuidas en diferentes módulos del proyecto.

El objetivo es centralizar toda la configuración para facilitar el mantenimiento y evitar duplicidad de información.

## Tareas

### 1.1 Localizar todas las credenciales

Buscar en todo el proyecto:

- API_URL
- DATABASE_URL
- claves de acceso
- nombres de loterías
- rutas
- constantes
- configuraciones repetidas

Identificar dónde se encuentran actualmente.

---

### 1.2 Centralizar la configuración

Crear un único punto de configuración.

Toda la aplicación deberá obtener la configuración desde ese lugar.

Ejemplo:

```
src/
    config/
        config.py
```

o

```
src/
    config.py
```

La decisión deberá favorecer la menor cantidad posible de carpetas.

---

### 1.3 Variables de entorno

Mover todas las credenciales a variables de entorno.

Ejemplo:

```
DATABASE_URL
API_URL
API_KEY
MODEL_PATH
```

Nunca dejar credenciales escritas directamente en el código, crear un archivo en la raiz del proyecto para que el editor sepa cuales son, y que nombres asignarles en los secrets de Github.

---

### 1.4 Actualizar el proyecto

Modificar todos los módulos para que utilicen exclusivamente la nueva configuración centralizada.

Eliminar cualquier configuración duplicada.

---

## Resultado esperado

- Existe un único archivo responsable de la configuración.
- No existen credenciales repetidas.
- No existen credenciales escritas directamente en el código.
- Todos los módulos utilizan el mismo sistema de configuración.

---

# Objetivo 2 - Limpieza del proyecto

## Descripción

Actualmente el proyecto genera archivos de log y contiene funciones destinadas únicamente al registro de información que ya no son necesarias.

El objetivo es simplificar el proyecto eliminando código muerto y archivos innecesarios.

---

## Tareas

### 2.1 Localizar el sistema de logging

Buscar:

- logger.py
- funciones write_log()
- save_log()
- append_log()
- creación automática de archivos .log
- carpetas logs/

---

### 2.2 Eliminar logs persistentes

Eliminar:

- carpetas de logs
- archivos .log
- funciones que escriben archivos de log

No deben generarse archivos durante la ejecución.

---

### 2.3 Simplificar mensajes

Mantener únicamente mensajes informativos por consola cuando sean realmente útiles.

No crear archivos temporales.

No guardar históricos de ejecución.

---

### 2.4 Eliminar código muerto

Eliminar:

- funciones nunca utilizadas
- imports innecesarios
- clases sin uso
- archivos obsoletos
- dependencias relacionadas con logging

---

## Resultado esperado

- El proyecto no genera archivos de log.
- Se elimina código innecesario.
- Se reduce la cantidad de archivos del proyecto.
- El código queda más simple y fácil de mantener.

---

# Objetivo 3 - Workflow de actualización automática

## Nombre

```
Auto_Neon_Sync
```

---

## Objetivo


Crear un GitHub Actions Workflow encargado exclusivamente de mantener actualizada la base de datos Neon.

Este workflow no debe entrenar modelos ni generar predicciones.

Su única responsabilidad será mantener sincronizada la información histórica.

---

## Frecuencia

Configurar el workflow para:

- ejecutarse automáticamente cada 3 días;
- ejecutarse una única vez por día al mediio dia;
- permitir ejecución manual mediante `workflow_dispatch`.

---

## Flujo esperado

```
Inicio

↓

Conectar a Neon

↓

Consultar la última fecha registrada

↓

Calcular la fecha de ayer

↓

¿Existen fechas pendientes?

        │

      No

        │

Finalizar

        │

      Sí

↓

Consultar la Ruta Oficial de Loterías

↓

Descargar únicamente los registros faltantes

↓

Insertar nuevos registros

↓

Actualizar registros existentes si cambiaron

↓

Finalizar
```

---

## Reglas

- Nunca descargar nuevamente todo el histórico.
- Utilizar siempre actualización incremental.
- No insertar registros duplicados.
- No eliminar registros existentes.
- Mantener la integridad de la base de datos.

---

## Resultado esperado

Cada ejecución del workflow deberá dejar Neon completamente sincronizado hasta el día anterior.

---

# Restricciones

Durante esta refactorización NO se debe:

- modificar la lógica de predicción;
- modificar el algoritmo de entrenamiento;
- cambiar la estructura de la base de datos;
- cambiar la forma en que actualmente se consulta la API oficial de loteria.

El objetivo es únicamente mejorar la arquitectura y automatizar la actualización de datos.

---

# Criterios de aceptación

La implementación se considerará finalizada cuando se cumplan todos los siguientes puntos:

## Configuración

- Existe un único módulo de configuración.
- Todas las credenciales utilizan variables de entorno.
- No existen configuraciones duplicadas.

---

## Limpieza

- No existen carpetas de logs.
- No se generan archivos `.log`.
- Se eliminó el código muerto relacionado con logging.
- El proyecto contiene menos archivos y menos dependencias innecesarias.

---

## Workflow

Existe un workflow llamado:

```
Auto_Neon_Sync
```

que:

- actualiza automáticamente la base de datos;
- utiliza la Ruta Oficial de Loterías;
- consulta únicamente las fechas faltantes;
- sincroniza Neon sin duplicar información;
- puede ejecutarse manualmente desde GitHub Actions.

---

# Definición de éxito

La refactorización estará completa cuando el proyecto tenga una arquitectura más simple, con una configuración centralizada, sin generación innecesaria de archivos de log y con un proceso automatizado que mantenga la base de datos Neon sincronizada de forma periódica mediante el workflow `Auto_Neon_Sync`.