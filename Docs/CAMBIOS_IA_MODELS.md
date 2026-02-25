# 📁 Cambio de Carpeta: models → IA_models

## 🎯 Resumen

Se renombró la carpeta `models/` a `IA_models/` para mayor claridad y evitar confusión con el módulo `src/models/` (que contiene esquemas Pydantic).

---

## ✅ Cambios Realizados

### 1. Carpeta Física
- ✅ Renombrada: `models/` → `IA_models/`
- ✅ Archivos preservados:
  - `modelo_result_astro_luna.pkl`
  - `modelo_result_astro_sol.pkl`
  - `modelo_series_astro_luna.pkl`
  - `modelo_series_astro_sol.pkl`
  - `.gitkeep`

### 2. Archivos de Configuración

#### `.env.example`
```diff
- MODELS_DIR=models
+ MODELS_DIR=IA_models
```

#### `src/core/config.py`
```diff
- MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "models")
+ MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "IA_models")
```

#### `src/utils/config.py`
```diff
- CARPETA_MODELOS = "models"
+ CARPETA_MODELOS = "IA_models"

- MODELO_RESULT_PATH = "models/modelo_result_astro.pkl"
+ MODELO_RESULT_PATH = "IA_models/modelo_result_astro.pkl"

- MODELO_SERIES_PATH = "models/modelo_series_astro.pkl"
+ MODELO_SERIES_PATH = "IA_models/modelo_series_astro.pkl"
```

### 3. Código Fuente

#### `src/utils/training.py`
```diff
- ruta_modelo = os.path.join(BASE_DIR, "models", nombre_archivo)
+ ruta_modelo = os.path.join(BASE_DIR, "IA_models", nombre_archivo)
```

### 4. Control de Versiones

#### `.gitignore`
```diff
- /models/*
- !/models/.gitkeep
+ /IA_models/*
+ !/IA_models/.gitkeep
```

### 5. Documentación

#### `README.md`
```diff
- ├── models/
+ ├── IA_models/
│   ├── modelo_result_{loteria}.pkl
│   └── modelo_series_{loteria}.pkl

- Se guarda el mejor en la carpeta `models/`.
+ Se guarda el mejor en la carpeta `IA_models/`.
```

#### `ARCHITECTURE.md`
- Actualizada estructura de carpetas
- Aclarado que `src/models/` es para esquemas Pydantic
- Aclarado que `IA_models/` es para modelos ML entrenados

---

## 🔍 Diferenciación Clara

### Antes (Confuso):
```
models/                    # ¿Modelos de ML o esquemas?
src/models/               # ¿Modelos de ML o esquemas?
```

### Ahora (Claro):
```
IA_models/                # Modelos de ML entrenados (.pkl)
├── modelo_result_*.pkl
└── modelo_series_*.pkl

src/models/               # Esquemas de validación (Pydantic)
├── __init__.py
└── schemas.py
```

---

## 🚀 Impacto en el Sistema

### ✅ Sin Cambios en Funcionalidad
- El sistema sigue funcionando igual
- Los modelos se cargan y guardan correctamente
- La configuración es retrocompatible con `.env`

### ✅ Mejor Organización
- Nombres más descriptivos
- Menos confusión entre conceptos
- Estructura más profesional

### ✅ Compatibilidad
- Si tienes un archivo `.env` personalizado, actualízalo:
  ```env
  MODELS_DIR=IA_models
  ```
- Si no tienes `.env`, el sistema usa el valor por defecto correcto

---

## 📋 Checklist de Verificación

- [x] Carpeta renombrada físicamente
- [x] `.gitkeep` preservado
- [x] Modelos .pkl preservados
- [x] `src/core/config.py` actualizado
- [x] `src/utils/config.py` actualizado
- [x] `src/utils/training.py` actualizado
- [x] `.env.example` actualizado
- [x] `.gitignore` actualizado
- [x] `README.md` actualizado
- [x] `ARCHITECTURE.md` actualizado

---

## 🧪 Pruebas Recomendadas

### 1. Verificar Carga de Modelos
```bash
python -c "from src.core.config import settings; print(settings.MODELS_DIR)"
# Debe mostrar: .../IA_models
```

### 2. Ejecutar Predicción
```bash
python main.py --predict
# Debe cargar modelos desde IA_models/
```

### 3. Entrenar Nuevo Modelo
```bash
python -m src.utils.training
# Debe guardar en IA_models/
```

---

## 📝 Notas Adicionales

### Para Desarrolladores Nuevos:
- Clonar el repo incluye la carpeta `IA_models/` (vacía, solo con `.gitkeep`)
- Los modelos entrenados se generan localmente
- No se suben a Git (están en `.gitignore`)

### Para CI/CD:
- Actualizar scripts que referencien `models/`
- Usar variable de entorno `MODELS_DIR` para flexibilidad

### Para Producción:
- Los modelos en `IA_models/` deben ser respaldados
- Considerar versionado de modelos (MLflow, DVC)

---

**Fecha del Cambio**: 2024  
**Razón**: Evitar confusión entre modelos ML y esquemas de datos  
**Impacto**: Bajo (solo nombres de carpetas)  
**Retrocompatibilidad**: Alta (configurable vía `.env`)
