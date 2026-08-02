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

    # ======================================================
    # MODO DE ENTRENAMIENTO
    # test  → ejecución rápida, comprobación de funcionamiento
    # prod  → entrenamiento realista, mejor parametrizado
    # ======================================================

    TRAINING_MODE: str = os.getenv("TRAINING_MODE", "prod").lower()

    # Perfiles por modo
    _TRAINING_PROFILES: dict = {
        "test": {
            "min_accuracy":      0.01,
            "max_iter":          2,
            "n_estimators":      [20, 30],
            "max_depth":         [3, 4],
            "min_samples_split": [4],
            "test_size":         0.3,
            "min_records":       20,
            "verbose":           True,
            "n_jobs":            1,      # secuencial en test
            "patience":          2,      # no aplica en test pero se define
        },
        "prod": {
            "min_accuracy":      0.05,
            "test_size":         0.2,
            "min_records":       50,
            "verbose":           True,
            "n_jobs":            -1,     # usa todos los núcleos disponibles
            # ── Espacio de búsqueda de hiperparámetros ──────────────────
            "n_estimators":      [100, 150, 200, 250, 300],
            "max_depth":         [4, 5, 6, 8, None],
            "min_samples_split": [2, 3, 5, 7],
            # ── Parámetros del algoritmo genético ───────────────────────
            "generaciones":      15,     # número de generaciones
            "poblacion":         8,      # individuos por generación
            "elite":             2,      # cuántos pasan directos a la siguiente gen
            "prob_mutacion":     0.3,    # probabilidad de mutar cada gen
            "patience":          5,      # early stop si no mejora en N generaciones
        },
    }

    @classmethod
    def get_training_profile(cls) -> dict:
        """Retorna el perfil de entrenamiento según TRAINING_MODE.
        Lee os.environ en tiempo de ejecución para respetar cambios por CLI."""
        mode = os.getenv("TRAINING_MODE", "prod").lower()
        if mode not in cls._TRAINING_PROFILES:
            print(f"⚠️  TRAINING_MODE='{mode}' desconocido. Usando 'prod'.")
            mode = "prod"
        return cls._TRAINING_PROFILES[mode]

    # TRAINING_CONFIGURE se construye dinámicamente (ver ensure_directories)
    TRAINING_CONFIGURE: dict = {}


    MODEL_TYPES = ["result", "series"]

    # Separador de logs
    LOG_SEPARATOR = "=" * 70


    # ======================================================
    # EVOLUTIONARY TRAINING CONFIG
    # ======================================================

    EVOLUTION_GENERATIONS = 10
    EVOLUTION_POPULATION_SIZE = 8
    EVOLUTION_ELITE_SIZE = 3

    EVOLUTIONARY_MAX_ITERATIONS = 10000
    EVOLUTIONARY_PATIENCE = 100


    # ======================================================
    # RANDOM FOREST SEARCH SPACE
    # ======================================================

    RF_N_ESTIMATORS_RANGE = (20, 100)
    RF_MAX_DEPTH_OPTIONS = [3, 4, 5, 6, None]
    RF_MIN_SAMPLES_SPLIT_RANGE = (2, 8)

    MUTATION_PROBABILITY = 0.4
    MUTATION_ESTIMATOR_STEP = 50
    N_JOBS = 1   # 1 = sin paralelismo (evita MemoryError en equipos con poca RAM)

    mutations = {
        "n_estimators": [100, 150, 200, 250, 300],
        "max_depth": [3, 4, 5, 6, 7, 8],
        "min_samples_split": [2, 3, 5, 7, 10],

        "mutation_probability": 0.8,
        "Mutation_estimator_step": 50,
        "n_jobs": -1,
    }

    MODEL_RANDOM_STATE_RANGE = (0, 10000)


    # ======================================================
    # MODEL VARIANTS
    # ======================================================

    MODEL_VARIANTS = [
        {
            "id": 1,
            "role": "PRODUCTION",
            "n_estimators": 200,
            "max_depth": 4,
            "min_samples_split": 5,
            "random_state": 42
        },
        {
            "id": 2,
            "role": "EXPERIMENTAL_1",
            "n_estimators": 150,
            "max_depth": 6,
            "min_samples_split": 3,
            "random_state": 123
        },
        {
            "id": 3,
            "role": "EXPERIMENTAL_2",
            "n_estimators": 250,
            "max_depth": 3,
            "min_samples_split": 7,
            "random_state": 456
        }
    ]


    # ======================================================
    # DIRECTORIOS BASE
    # ======================================================

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "IA_models")
    DATA_DIR: Path = BASE_DIR / os.getenv("DATA_DIR", "data")

    # ======================================================
    # API CONFIG
    # ======================================================

    # ======================================================
    # DATABASE CONFIG
    # ======================================================

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    API_URL: str = os.getenv("BASE_URL", "https://superastro.com.co/historico.php")
    CLAVES_UNICAS: list[str] = ["fecha", "lottery", "result", "series"]
    SCRAPER_DELAY_DEFAULT: float = 1.0
    SCRAPER_REQUEST_TIMEOUT: int = 10
    zodiaco: dict[str,str] = {
        'ARIES': 'ARI',
        'TAURO': 'TAU',
        'GEMINIS': 'GEM',
        'GÉMINIS': 'GEM',
        'CANCER': 'CAN',
        'CÁNCER': 'CAN',
        'LEO': 'LEO',
        'VIRGO': 'VIR',
        'LIBRA': 'LIB',
        'ESCORPIO': 'ESC',
        'ESCORPION': 'ESC',
        'SAGITARIO': 'SAG',
        'CAPRICORNIO': 'CAP',
        'ACUARIO': 'ACU',
        'PISCIS': 'PIS'
    }
    
    # ======================================================
    # LOTTERY CONFIG
    # ======================================================


#-------------------------------------------------------------------------------------------------------
    # ======================================================
    # API CONFIG
    # ======================================================

    FIND_LOTERY: str = os.getenv("FIND_LOTERY", "ASTRO")

    # ======================================================
    # ADVANCED ML CONFIG
    # ======================================================

    USE_ADVANCED_ML: bool = os.getenv(
        "USE_ADVANCED_ML",
        "false"
    ).lower() == "true"

    ML_ALGORITHM: str = os.getenv(
        "ML_ALGORITHM",
        "RandomForest"
    )

    HYPERPARAMETER_SEARCH: str = os.getenv(
        "HYPERPARAMETER_SEARCH",
        "random"
    )

    SEARCH_ITERATIONS: int = int(os.getenv("SEARCH_ITERATIONS", "10"))
    CV_FOLDS: int = int(os.getenv("CV_FOLDS", "5"))

    ENABLE_FEATURE_ENGINEERING: bool = os.getenv(
        "ENABLE_FEATURE_ENGINEERING",
        "true"
    ).lower() == "true"

    # ======================================================
    # LOGGING
    # ======================================================

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


    # ======================================================
    # FILE CONFIG
    # ======================================================

    EXCEL_FILENAME: str = f"resultados_{FIND_LOTERY.lower()}.xlsx"
    RESULTS_JSON: str = "results.json"

    # ======================================================
    # PATH HELPERS
    # ======================================================

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
        """
        filename = f"modelo_{model_type}_{lottery_name.lower().replace(' ', '_')}.pkl"
        return cls.MODELS_DIR / filename


    @classmethod
    def ensure_directories(cls) -> None:
        """Crea los directorios necesarios y construye TRAINING_CONFIGURE."""
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Construir TRAINING_CONFIGURE desde el perfil activo
        profile = cls.get_training_profile()
        cls.TRAINING_CONFIGURE = {
            "min_accuracy":    profile["min_accuracy"],
            # max_iterations: en modo genético = generaciones × poblacion
            "max_iterations":  profile.get("generaciones", profile.get("max_iter", 10))
                               * profile.get("poblacion", 1),
            "min_records":     profile["min_records"],
            "training_verbose": profile["verbose"],
            # legacy keys
            "iterations":      profile.get("max_iter", profile.get("generaciones", 10)),
            "max_training_logs": 3,
        }


# Instancia global
settings = Settings()

# Crear directorios automáticamente
settings.ensure_directories()
