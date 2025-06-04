import logging
import os

def configurar_logger(nombre_logger="LoteryLogger", archivo_log="log_loteria.log"):
    logger = logging.getLogger(nombre_logger)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(f"logs/{archivo_log}", encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger
