import os
import joblib
from datetime import datetime
from src.core.config import settings


# ======================================================
# CREAR BASE FIJA DE MEMORIA IA
# ======================================================
def crear_base_modelos_IA(nombre_loteria: str) -> dict:

    modelos_dir = settings.MODELS_DIR
    os.makedirs(modelos_dir, exist_ok=True)

    nombre_clean = nombre_loteria.lower().replace(" ", "_")

    result_paths = [
        os.path.join(modelos_dir, f"1_{nombre_clean}_result.pkl"),
        os.path.join(modelos_dir, f"2_{nombre_clean}_result.pkl"),
    ]

    series_paths = [
        os.path.join(modelos_dir, f"1_{nombre_clean}_series.pkl"),
        os.path.join(modelos_dir, f"2_{nombre_clean}_series.pkl"),
    ]

    return {
        "result": result_paths,
        "series": series_paths
    }


# ======================================================
# SELECCIONAR SLOT A REEMPLAZAR
# ======================================================
def seleccionar_slot_a_reemplazar(paths: list) -> str:
    """
    Devuelve el modelo con menor accuracy.
    Si alguno no existe → usa ese primero.
    """

    modelos = []

    for path in paths:

        # Slot libre
        if not os.path.exists(path):
            return path

        try:
            data = joblib.load(path)
            acc = data.get("accuracy", 0)
        except Exception:
            acc = 0

        modelos.append((path, acc))

    peor_path, _ = min(modelos, key=lambda x: x[1])

    return peor_path


# ======================================================
# GUARDADO EVOLUTIVO DE MODELOS IA
# ======================================================
def guardar_modelo_si_mejora(
    nombre_loteria: str,
    tipo_modelo: str,
    modelo,
    accuracy: float
) -> bool:

    if modelo is None:
        return False

    try:
        base = crear_base_modelos_IA(nombre_loteria)

        paths = base[tipo_modelo]

        modelo_path = seleccionar_slot_a_reemplazar(paths)

        payload = {
            "model": modelo,
            "accuracy": float(accuracy),
            "timestamp": datetime.now()
        }

        joblib.dump(payload, modelo_path)

        print(
            f"🧠 Slot actualizado → {os.path.basename(modelo_path)} "
            f"(Acc: {accuracy:.4f})"
        )

        return True

    except Exception as e:
        print(f"❌ Error guardando modelo: {e}")
        return False