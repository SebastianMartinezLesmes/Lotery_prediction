# 🎰 Sistema de Predicción de Lotería

Este sistema automatizado desarrollado en Python permite la predicción de resultados de lotería mediante Machine Learning. Incluye:

- Recolección de datos desde archivos Excel y APIs externas.
- Entrenamiento y perfeccionamiento de modelos por cada lotería individual.
- Uso de modelos de regresión logística y árboles de decisión.
- Entrenamiento dividido en predicción por resultados (`result`) y por secuencias (`series`).
- Gestión automática de modelos en formato `.pkl`.
- Limpieza automática de archivos de caché (`__pycache__`).
- Registro detallado de logs para diagnóstico y auditoría.

---

## 📁 Estructura del Proyecto

```
LOTTERY_PREDICTION/
├── index.py
├── README.md
├── LICENCE
├── .gitignore
├── data/
│   └── resultados_*.xlsx
├── logs/
│   ├── dependencias.log
│   └── log_loteria.log
├── IA_models/
│   ├── modelo_result_{loteria}.pkl
│   └── modelo_series_{loteria}.pkl
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
│   │   ├── training.py
│   │   ├── logger.py
│   │   ├── prediction.py
│   │   ├── result.py
│   │   └── zodiaco.py
```

---

## 🚀 Ejecución del Sistema

### Opción 1: Pipeline completo (recomendado)

```bash
python index.py
```

Este comando ejecuta el pipeline completo:
1. Instalación/verificación de dependencias
2. Recolección o actualización de datos desde Excel/API
3. Predicción de resultados usando modelos previamente entrenados
4. Limpieza de archivos de caché

### Opción 2: CLI con componentes individuales

```bash
# Ver configuración actual
python main.py --config

# Ejecutar pipeline completo
python main.py

# Solo verificar dependencias
python main.py --deps

# Solo recolectar datos
python main.py --collect

# Solo entrenar modelos
python main.py --train

# Solo generar predicciones
python main.py --predict

# Predicción para lotería específica
python main.py --predict --lottery ASTRO

# Ver ayuda
python main.py --help
```

### Opción 3: Entrenamiento directo de modelos

```bash
python -m src.utils.training
```

Esto buscará los modelos `.pkl` previamente creados por lotería. Si existen, los perfeccionará. Si no se encuentra ningún modelo previo, se mostrará un mensaje:  
**"Loterías no encontradas"**

---

## 🧠 Funcionamiento del Sistema de Machine Learning

El flujo general de predicción y entrenamiento incluye:

1. **Carga de Datos:**  
   Desde `resultados_*.xlsx`, usando `read_excel.py`.

2. **Preprocesamiento:**  
   Generación de secuencias n-gram para series y codificación para predicción de resultados.

3. **Entrenamiento de Modelos:**  
   Se crean dos modelos independientes por cada lotería:

   - `modelo_result_{loteria}.pkl`: para predecir el número y símbolo ganador.
   - `modelo_series_{loteria}.pkl`: para aprender secuencias históricas usando n-gramas.

4. **Evaluación:**  
   Se comparan modelos mediante validación cruzada y se guarda el mejor en la carpeta `IA_models/`.

5. **Predicción:**  
   Basada en patrones aprendidos para cada lotería de forma individual.

---

## 📊 Datos de Entrada

Los datos provienen de archivos como:

```
data/resultados_astro.xlsx
```

El sistema los crea automáticamente si no existen, usando fuentes disponibles.

---

## 📋 Registro de Logs

Todos los eventos se registran en:

- `logs/dependencias.log` — instalación de paquetes
- `logs/log_loteria.log` — seguimiento del sistema
- `logs/tiempos.log` — Registro de tiempos de ejecusion

---

## 🧹 Limpieza de Caché

Automática al final del flujo completo. También puedes ejecutarla manualmente:

```bash
python -m src.utils.drop_cache
```

---

## 📦 Dependencias

Las dependencias necesarias se cargan automáticamente desde:

```
src/utils/dependencies.py
```

---

## ⚙️ Orden de Ejecución de Scripts

Puedes modificar la ejecución del sistema en `index.py`:

```python
scripts = [
    ("Dependencias", "src/utils/dependencies.py"),
    ("Recolección de Datos", "src/excel/read_excel.py"),
    ("Predicción", "src/utils/prediction.py")
]
```

---

## ✅ Requisitos

- Python 3.8+
- pip

### Instalación de dependencias:

```bash
# Instalar todas las dependencias
pip install -r requirements.txt

# O ejecutar el sistema (instala automáticamente)
python index.py
```

### Configuración:

1. Copiar el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Editar `.env` con tus valores:
```env
FIND_LOTERY=ASTRO
ITERATIONS=8000
MIN_ACCURACY=0.7
```

---

## 🧠 Autor / Créditos

Proyecto desarrollado por **Juan Sebastian Martinez Lesmes**  
Implementando técnicas de Machine Learning y procesamiento automatizado de datos para la predicción de resultados en el sector de juegos de azar y predicción de resultados.

---