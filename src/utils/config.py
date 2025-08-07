# -----------------------------------
# 🔍 GENERAL PROJECT CONFIGURATION 
# -----------------------------------

# Target lottery name (used in the API and Excel file name)
FIND_LOTERY = "ASTRO"

# Name of the Excel file to create or read / read_excel.py, excel.py
CREATE_DOC = f"resultados_{FIND_LOTERY.lower()}.xlsx"

# -----------------------------------
# 🌐 API CONFIGURATION
# -----------------------------------

API_URL = "https://api-resultadosloterias.com/api/results/"
FECHA_DEFECTO = "2023-02-01"
CLAVES_UNICAS = ["lottery", "slug", "date", "result", "series"]

# -----------------------------------
# 🧠 PREDICTION / TRAINING CONFIGURATION
# -----------------------------------

ITERATIONS = 8000
MIN_ACCURACY  = 0.7

# 📁 File's routers for best models
MODELO_RESULT_PATH = "models/modelo_result_astro.pkl"
MODELO_SERIES_PATH = "models/modelo_series_astro.pkl"

# -----------------------------------
# 📂 Prediction.py
# -----------------------------------

ARCHIVO_EXCEL = CREATE_DOC
TIEMPOS_LOG = "logs/tiempos.log"
CARPETA_MODELOS = "models"
