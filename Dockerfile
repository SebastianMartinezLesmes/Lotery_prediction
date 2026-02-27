# Dockerfile para Sistema de Predicción de Lotería
# Imagen base con Python 3.11
FROM python:3.11-slim

# Metadata
LABEL maintainer="Juan Sebastian Martinez Lesmes"
LABEL description="Sistema de Predicción de Lotería con Machine Learning"
LABEL version="2.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 lottery && \
    mkdir -p /app && \
    chown -R lottery:lottery /app

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY --chown=lottery:lottery requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY --chown=lottery:lottery . .

# Crear directorios necesarios
RUN mkdir -p IA_models data logs && \
    chown -R lottery:lottery IA_models data logs

# Cambiar a usuario no-root
USER lottery

# Exponer puerto (si se implementa API en el futuro)
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando por defecto
CMD ["python", "main.py", "--help"]
