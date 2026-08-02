import os
import joblib
from datetime import datetime
from src.core.config import settings
from src.features.feature_engineering import FEATURE_COLUMNS


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
    Devuelve el slot con menor accuracy.
    Si alguno no existe → usa ese primero.
    """
    modelos = []

    for path in paths:
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
# GUARDADO EVOLUTIVO CON METADATA COMPLETA (Paso 7)
# ======================================================
def guardar_modelo_si_mejora(
    nombre_loteria: str,
    tipo_modelo: str,
    modelo,
    accuracy: float,
    f1_score: float = None,
    n_records: int = None,
) -> bool:
    """
    Guarda el modelo en el slot de menor accuracy si el nuevo lo supera.
    Incluye metadata completa para trazabilidad.
    """
    if modelo is None:
        return False

    try:
        base = crear_base_modelos_IA(nombre_loteria)
        paths = base[tipo_modelo]
        modelo_path = seleccionar_slot_a_reemplazar(paths)

        # Verificar si el nuevo modelo supera al que está en ese slot
        if os.path.exists(modelo_path):
            try:
                existente = joblib.load(modelo_path)
                acc_existente = existente.get("accuracy", 0)
                if accuracy <= acc_existente:
                    print(
                        f"  ↔ Sin mejora en {os.path.basename(modelo_path)} "
                        f"(actual={acc_existente:.4f}, nuevo={accuracy:.4f})"
                    )
                    return False
            except Exception:
                pass

        # Detectar tipo de algoritmo
        tipo_algo = type(modelo).__name__

        # Paso 7: payload con metadata completa
        payload = {
            "model":          modelo,
            "accuracy":       float(accuracy),
            "f1_score":       float(f1_score) if f1_score is not None else None,
            "algoritmo":      tipo_algo,
            "n_features":     getattr(modelo, "n_features_in_", len(FEATURE_COLUMNS)),
            "feature_names":  FEATURE_COLUMNS,
            "n_records":      n_records,
            "loteria":        nombre_loteria,
            "tipo_modelo":    tipo_modelo,
            "params":         modelo.get_params() if hasattr(modelo, "get_params") else {},
            "timestamp":      datetime.now().isoformat(),
        }

        joblib.dump(payload, modelo_path)

        print(
            f"  ✅ {os.path.basename(modelo_path)} actualizado "
            f"[{tipo_algo}] Acc={accuracy:.4f}"
            + (f" F1={f1_score:.4f}" if f1_score else "")
        )
        return True

    except Exception as e:
        print(f"❌ Error guardando modelo: {e}")
        return False