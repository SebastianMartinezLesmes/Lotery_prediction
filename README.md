# 🎰 Sistema de Predicción de Lotería
El usuario está desarrollando un sistema automatizado de predicción de lotería utilizando Python. Este sistema incluye:

- Recolección de datos desde archivos Excel y APIs externas.
- Implementación de modelos de Machine Learning, como regresión logística y árboles de decisión, para la predicción de resultados.
- Limpieza automática de archivos de caché (__pycache__).
- Generación y gestión de registros (logs) para el seguimiento del funcionamiento del sistema.

---

## 📁 Estructura del Proyecto

```
LOTTERY_PREDICTION/
├── index.py
├── README.md
├── LICENCE
├── .gitignore
├── data/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── models/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── API.py 
│   ├── excel/
│   │   ├── __init__.py
│   │   ├── excel.py
│   │   └── read_excel.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── drop_cache.py
│   │   ├── entrenamiento.py
│   │   ├── logger.py
│   │   └── prediction.py
│   │   └── result.py
```
---

## 🚀 Ejecución del Sistema

### Opción 1: Modo estándar (con logs)

```bash
python index.py
```
Este comando ejecutará en orden:

1. Instalación automática de dependencias

2. Recolección de datos desde Excel/API

3. Predicción de resultados

4. Limpieza de caché
---

## 🧹 Limpieza de Caché

Al final de la ejecución, el sistema ejecuta un módulo para eliminar todas las carpetas `__pycache__` del proyecto.

También puedes ejecutarlo de forma independiente:

```bash
python -m src.utils.drop_cache
```

---

## 📦 Dependencias

El sistema carga e instala automáticamente las dependencias necesarias en el primer paso (`dependencies.py`).

Puedes revisar o modificar las dependencias requeridas en:

```
src/utils/dependencies.py
```

---

## 📋 Registro de Logs
El sistema genera logs detallados para seguimiento y depuración en:

- Registro principal: logs/log_loteria.log
- Registro de instalación de dependencias: logs/dependencias.log
---

## ⚙️ Personalización de Scripts

Puedes modificar la lista de scripts ejecutados en el archivo:

```python
# index.py 
scripts = [
    ("Dependencias", "src/utils/dependencies.py"),
    ("Recolección de Datos", "src/excel/read_excel.py"),
    ("Predicción", "prediction.py")
]
```
---

## 📦 Dependencias

Las dependencias se gestionan automáticamente en: 
```
src/utils/dependencies.py
```
## 📊 Datos de Entrada

El archivo resultados_X_.xlsx contiene los datos históricos de los resultados de la lotería y funciona como la fuente principal de entrada para el sistema de predicción. Si el archivo no existe, el script exel.py se encarga de generarlo automáticamente y completar su contenido mediante consultas a los registros más antiguos disponibles. 

## 🧠 Autor / Créditos

- Desarrollado con ❤️ para automatizar predicciones de lotería.
- Incluye limpieza de cachés, logs, manejo de errores y progresos visuales.

---

## 🧠 Funcionamiento del Sistema de Machine Learning
El archivo prediction.py contiene la lógica de predicción basada en Machine Learning. El flujo general de este módulo es:

1. Carga de Datos:
Se importan y limpian los datos desde el archivo resultados_astro.xlsx mediante funciones del módulo read_excel.py.

2. Preparación de los Datos:
Se convierten las secuencias históricas en características útiles, aplicando técnicas de n-gramas (por ejemplo, combinaciones de 2 o 3 resultados previos).

3. Entrenamiento del Modelo:
Se entrenan dos modelos principales:

- Regresión logística
- Árboles de decisión (DecisionTreeClassifier)

4. Evaluación del Modelo:
Se realiza validación cruzada para determinar qué modelo ofrece mejor precisión según los datos históricos.

5. Predicción:
El sistema genera una predicción del número y símbolo más probable en el próximo sorteo basándose en los patrones detectados.

6. Salida:
Se imprime o almacena el resultado predicho, acompañado de métricas de confianza y logs.

Este sistema no se basa en azar, sino en la detección de patrones repetitivos que pueden tener alguna correlación estadística, aunque no se garantiza la certeza del resultado.

## ⚠️ Requisitos

- Python 3.8+
- pip 

---