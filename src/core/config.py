"""
Configuración centralizada del sistema con soporte para múltiples entornos.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    """Configuración global del sistema."""
    
    # Directorios base
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "IA_models")
    DATA_DIR: Path = BASE_DIR / os.getenv("DATA_DIR", "data")
    LOGS_DIR: Path = BASE_DIR / os.getenv("LOGS_DIR", "logs")
    
    # API Configuration
    API_URL: str = os.getenv("API_URL", "https://api-resultadosloterias.com/api/results/")
    FECHA_DEFECTO: str = os.getenv("FECHA_DEFECTO", "2023-02-01")
    
    # Lottery Configuration
    FIND_LOTERY: str = os.getenv("FIND_LOTERY", "ASTRO")
    
    # Model Training
    ITERATIONS: int = int(os.getenv("ITERATIONS", "8000"))
    MIN_ACCURACY: float = float(os.getenv("MIN_ACCURACY", "0.7"))
    MAX_TRAINING_LOGS: int = int(os.getenv("MAX_TRAINING_LOGS", "3"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Archivos
    EXCEL_FILENAME: str = f"resultados_{FIND_LOTERY.lower()}.xlsx"
    RESULTS_JSON: str = "results.json"
    
    # Claves únicas para deduplicación
    CLAVES_UNICAS: list[str] = ["lottery", "slug", "date", "result", "series"]
    
    @classmethod
    def get_excel_path(cls) -> Path:
        """Retorna la ruta completa al archivo Excel."""
        return cls.DATA_DIR / cls.EXCEL_FILENAME
    
    @classmethod
    def get_results_path(cls) -> Path:
        """Retorna la ruta completa al archivo de resultados JSON."""
        return cls.DATA_DIR / cls.RESULTS_JSON
    
    @classmethod
    def get_model_path(cls, lottery_name: str, model_type: str) -> Path:
        """
        Genera la ruta para un modelo específico.
        
        Args:
            lottery_name: Nombre de la lotería
            model_type: Tipo de modelo ('result' o 'series')
        
        Returns:
            Path al archivo del modelo
        """
        filename = f"modelo_{model_type}_{lottery_name.lower().replace(' ', '_')}.pkl"
        return cls.MODELS_DIR / filename
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Crea los directorios necesarios si no existen."""
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Instancia global de configuración
settings = Settings()

# Crear directorios al importar
settings.ensure_directories()
