# 🎰 Sistema de Predicción de Lotería

Este proyecto automatiza el proceso de recolección de datos, predicción y limpieza de cachés para juegos de lotería. Proporciona un registro completo de eventos.

---

## 📁 Estructura del Proyecto

```
loteria/
├── index.py
├── wm_load.py
├── src/
│   ├── utils/
│   │   ├── dependencies.py
│   │   ├── drop_cache.py
│   │   ├── logger.py
│   │   └── __init__.py
│   ├── excel/
│   │   ├── read_excel.py
│   │   └── __init__.py
├── prediction.py
├── logs/
│   └── log_loteria.log
```

---

## 🚀 Ejecución del Sistema

### Opción 1: Modo estándar (con logs)

```bash
python index.py
```

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

Se genera un registro detallado de cada ejecución en:

```
logs/log_loteria.log
```

---

## 🔧 Personalización

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

## 🧠 Autor / Créditos

- Desarrollado con ❤️ para automatizar predicciones de lotería.
- Incluye limpieza de cachés, logs, manejo de errores y progresos visuales.

---

## ⚠️ Requisitos

- Python 3.8+

---
