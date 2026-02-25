# 🏗️ Arquitectura del Sistema - Mejoras Implementadas

## 📋 Resumen de Mejoras

Este documento describe las mejoras arquitectónicas implementadas en el sistema de predicción de lotería.

---

## 1️⃣ Separación de Configuración por Entorno

### Archivos Creados:
- `.env.example` - Plantilla de configuración
- `src/core/config.py` - Gestión centralizada de configuración

### Características:
- ✅ Variables de entorno con `python-dotenv`
- ✅ Configuración centralizada en clase `Settings`
- ✅ Valores por defecto seguros
- ✅ Métodos helper para rutas de archivos
- ✅ Creación automática de directorios

### Uso:
```python
from src.core.config import settings

# Acceder a configuración
print(settings.API_URL)
print(settings.ITERATIONS)

# Obtener rutas
excel_path = settings.get_excel_path()
model_path = settings.get_model_path("astro_sol", "result")
```

### Configurar:
1. Copiar `.env.example` a `.env`
2. Ajustar valores según el entorno
3. El sistema carga automáticamente las variables

---

## 2️⃣ Organización de Archivos por Carpetas

### Nueva Estructura:

```
src/
├── core/                    # Núcleo del sistema
│   ├── __init__.py
│   ├── config.py           # Configuración centralizada
│   ├── exceptions.py       # Excepciones personalizadas
│   ├── logger.py           # Sistema de logging mejorado
│   └── validators.py       # Validadores de datos
│
├── models/                  # Esquemas y validación (Pydantic)
│   ├── __init__.py
│   └── schemas.py          # Modelos Pydantic
│
├── api/                     # Consumo de APIs
│   ├── __init__.py
│   ├── API.py              # (legacy)
│   └── client.py           # Cliente HTTP mejorado
│
├── excel/                   # Manejo de Excel
│   ├── __init__.py
│   ├── excel.py
│   └── read_excel.py
│
└── utils/                   # Utilidades
    ├── __init__.py
    ├── training.py
    ├── prediction.py
    ├── result.py
    └── zodiaco.py

IA_models/                   # Modelos de ML entrenados (.pkl)
├── .gitkeep
├── modelo_result_*.pkl
└── modelo_series_*.pkl
```

### Principios:
- **core/**: Funcionalidad base compartida
- **models/**: Definición de estructuras de datos (Pydantic schemas)
- **api/**: Comunicación externa
- **excel/**: Persistencia de datos
- **utils/**: Lógica de negocio específica
- **IA_models/**: Modelos de Machine Learning entrenados (.pkl)

---

## 3️⃣ Manejo de Errores Robusto

### Excepciones Personalizadas (`src/core/exceptions.py`):

```python
LotteryPredictionError      # Base
├── DataValidationError     # Validación de datos
├── ModelNotFoundError      # Modelo no encontrado
├── ModelTrainingError      # Error en entrenamiento
├── APIError                # Error de API
├── ExcelError              # Error de Excel
└── InsufficientDataError   # Datos insuficientes
```

### Características:
- ✅ Jerarquía clara de excepciones
- ✅ Mensajes descriptivos
- ✅ Fácil captura por tipo
- ✅ Logging automático de errores

### Uso:
```python
from src.core.exceptions import APIError, DataValidationError

try:
    data = api_client.get_results()
except APIError as e:
    logger.error(f"Error de API: {e}")
    # Manejar error específico
except DataValidationError as e:
    logger.error(f"Datos inválidos: {e}")
    # Manejar validación
```

---

## 4️⃣ Validación de Datos con Pydantic

### Esquemas Creados (`src/models/schemas.py`):

1. **LotteryResult** - Resultado de lotería
2. **PredictionInput** - Entrada para predicción
3. **PredictionOutput** - Salida de predicción
4. **TrainingMetrics** - Métricas de entrenamiento
5. **APIResponse** - Respuesta de API
6. **ModelConfig** - Configuración de modelo

### Características:
- ✅ Validación automática de tipos
- ✅ Conversión de datos
- ✅ Validadores personalizados
- ✅ Mensajes de error claros
- ✅ Serialización JSON

### Ejemplo:
```python
from src.models.schemas import LotteryResult

# Validación automática
result = LotteryResult(
    fecha="2024-01-15",
    lottery="astro sol",
    result=1234,
    series="aries"
)

# Conversión automática
print(result.lottery)  # "ASTRO SOL" (uppercase)
print(result.fecha)    # date(2024, 1, 15)
```

### Validadores (`src/core/validators.py`):
- `validate_dataframe()` - Valida DataFrames
- `validate_lottery_results()` - Valida resultados
- `validate_training_data()` - Valida datos de entrenamiento
- `validate_model_path()` - Valida rutas de modelos

---

## 5️⃣ Type Hints Completos

### Beneficios:
- ✅ Autocompletado en IDEs
- ✅ Detección temprana de errores
- ✅ Documentación implícita
- ✅ Mejor mantenibilidad

### Ejemplo:
```python
from typing import List, Optional, Dict, Any
from datetime import date
import pandas as pd

def get_historical_results(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    lottery_filter: Optional[str] = None,
    show_progress: bool = True
) -> List[Dict[str, Any]]:
    """
    Obtiene resultados históricos.
    
    Args:
        fecha_inicio: Fecha de inicio
        fecha_fin: Fecha de fin
        lottery_filter: Filtro de lotería
        show_progress: Mostrar progreso
    
    Returns:
        Lista de resultados
    """
    pass
```

---

## 🔄 Cliente API Mejorado

### Archivo: `src/api/client.py`

### Características:
- ✅ Reintentos automáticos con backoff exponencial
- ✅ Timeout configurable
- ✅ Manejo de errores específico
- ✅ Context manager para gestión de recursos
- ✅ Logging detallado
- ✅ Filtrado y deduplicación
- ✅ Barra de progreso

### Uso:
```python
from src.api.client import LotteryAPIClient
from datetime import date

# Context manager (recomendado)
with LotteryAPIClient() as client:
    results = client.get_historical_results(
        fecha_inicio=date(2024, 1, 1),
        lottery_filter="ASTRO"
    )

# Uso manual
client = LotteryAPIClient(timeout=60, max_retries=5)
try:
    results = client.get_results_by_date(date.today())
finally:
    client.close()
```

---

## 📊 Sistema de Logging Mejorado

### Archivo: `src/core/logger.py`

### Características:
- ✅ Múltiples loggers especializados
- ✅ Formato consistente
- ✅ Salida a consola y archivo
- ✅ Niveles configurables
- ✅ Sin duplicación de handlers

### Loggers Disponibles:
```python
from src.core.logger import (
    get_main_logger,
    get_training_logger,
    get_api_logger,
    get_prediction_logger
)

logger = get_main_logger()
logger.info("Sistema iniciado")
logger.error("Error crítico", exc_info=True)
```

---

## 📦 Dependencias

### Archivo: `requirements.txt`

Nuevas dependencias agregadas:
- `python-dotenv` - Variables de entorno
- `pydantic` - Validación de datos

Instalar:
```bash
pip install -r requirements.txt
```

---

## 🚀 Próximos Pasos

### Migración Gradual:
1. ✅ Estructura base creada
2. ⏳ Refactorizar módulos existentes para usar nueva arquitectura
3. ⏳ Agregar tests unitarios
4. ⏳ Implementar mejoras de ML
5. ⏳ Crear API REST

### Compatibilidad:
- Los archivos legacy siguen funcionando
- Migración incremental sin romper funcionalidad
- Nuevos desarrollos usan la nueva arquitectura

---

## 📚 Documentación Adicional

- Ver ejemplos de uso en cada módulo
- Consultar docstrings para detalles de funciones
- Revisar type hints para entender interfaces

---

**Autor**: Sistema de Predicción de Lotería  
**Fecha**: 2024  
**Versión**: 2.0
