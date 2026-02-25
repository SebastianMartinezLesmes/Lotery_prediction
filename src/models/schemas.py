"""
Esquemas de validación de datos usando Pydantic.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LotteryResult(BaseModel):
    """Esquema para un resultado de lotería."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    fecha: date = Field(..., description="Fecha del sorteo")
    lottery: str = Field(..., min_length=1, description="Nombre de la lotería")
    slug: Optional[str] = Field(None, description="Slug identificador")
    result: int = Field(..., ge=0, le=9999, description="Número ganador (0-9999)")
    series: str = Field(..., description="Serie o símbolo zodiacal")
    
    @field_validator('lottery')
    @classmethod
    def lottery_uppercase(cls, v: str) -> str:
        """Convierte el nombre de la lotería a mayúsculas."""
        return v.upper().strip()
    
    @field_validator('series')
    @classmethod
    def series_uppercase(cls, v: str) -> str:
        """Convierte la serie a mayúsculas."""
        return v.upper().strip()
    
    @field_validator('fecha', mode='before')
    @classmethod
    def parse_fecha(cls, v):
        """Parsea diferentes formatos de fecha."""
        if isinstance(v, date):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            # Intentar diferentes formatos
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Formato de fecha no válido: {v}")
        raise ValueError(f"Tipo de fecha no soportado: {type(v)}")


class PredictionInput(BaseModel):
    """Datos de entrada para realizar una predicción."""
    
    dia: int = Field(..., ge=1, le=31, description="Día del mes")
    mes: int = Field(..., ge=1, le=12, description="Mes del año")
    anio: int = Field(..., ge=2000, le=2100, description="Año")
    dia_semana: int = Field(..., ge=0, le=6, description="Día de la semana (0=Lunes)")
    
    @classmethod
    def from_date(cls, fecha: date) -> "PredictionInput":
        """Crea una instancia desde un objeto date."""
        return cls(
            dia=fecha.day,
            mes=fecha.month,
            anio=fecha.year,
            dia_semana=fecha.weekday()
        )


class PredictionOutput(BaseModel):
    """Resultado de una predicción."""
    
    loteria: str = Field(..., description="Nombre de la lotería")
    numero: str = Field(..., pattern=r'^\d{4}$', description="Número predicho (4 dígitos)")
    simbolo: str = Field(..., description="Símbolo o signo zodiacal")
    fecha_prediccion: datetime = Field(default_factory=datetime.now)
    modelo_usado: Optional[str] = Field(None, description="Nombre del modelo utilizado")
    confianza: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nivel de confianza")
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class TrainingMetrics(BaseModel):
    """Métricas de entrenamiento de un modelo."""
    
    loteria: str
    tipo_modelo: str = Field(..., pattern=r'^(result|series)$')
    accuracy: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    intentos: int = Field(..., ge=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class APIResponse(BaseModel):
    """Respuesta de la API externa."""
    
    fecha: str
    resultados: List[dict]
    
    @field_validator('resultados')
    @classmethod
    def validate_resultados(cls, v: List[dict]) -> List[dict]:
        """Valida que los resultados tengan las claves necesarias."""
        required_keys = {'lottery', 'result', 'series'}
        for resultado in v:
            if not required_keys.issubset(resultado.keys()):
                raise ValueError(f"Resultado incompleto: {resultado}")
        return v


class ModelConfig(BaseModel):
    """Configuración de un modelo de ML."""
    
    n_estimators: int = Field(default=200, ge=10, le=1000)
    max_depth: Optional[int] = Field(default=4, ge=1, le=50)
    min_samples_split: int = Field(default=5, ge=2, le=20)
    class_weight: str = Field(default='balanced')
    random_state: Optional[int] = Field(default=42)
