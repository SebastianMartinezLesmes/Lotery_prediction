# 🐳 Docker Deployment

## Descripción

Guía completa para desplegar el Sistema de Predicción de Lotería usando Docker y Docker Compose, garantizando un entorno consistente y reproducible.

---

## 📋 Requisitos Previos

- Docker >= 20.10
- Docker Compose >= 2.0
- 2GB RAM mínimo
- 5GB espacio en disco

### Instalación de Docker

**Windows:**
- Descargar [Docker Desktop](https://www.docker.com/products/docker-desktop)

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Mac:**
- Descargar [Docker Desktop para Mac](https://www.docker.com/products/docker-desktop)

---

## 🚀 Inicio Rápido

### 1. Construir la imagen

```bash
docker build -t lottery-prediction:latest .
```

### 2. Ejecutar con Docker Compose

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

---

## 🔧 Configuración

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# API Configuration
API_URL=https://api-resultadosloterias.com/api/results/
FIND_LOTERY=ASTRO

# Training
ITERATIONS=1000
MIN_ACCURACY=0.7

# Logging
LOG_LEVEL=INFO

# Alerts
ALERT_ACCURACY_WARNING=0.6
ALERT_ACCURACY_CRITICAL=0.5

# Scheduler (opcional)
SCHEDULE_COLLECT_CRON="0 8 * * *"
SCHEDULE_TRAIN_CRON="0 2 * * 0"
```

---

## 📦 Servicios Disponibles

### lottery-system
Servicio principal del sistema.

```bash
# Ejecutar pipeline completo
docker-compose run --rm lottery-system python main.py

# Solo entrenamiento
docker-compose run --rm lottery-system python main.py --train

# Solo predicción
docker-compose run --rm lottery-system python main.py --predict

# Batch predictions
docker-compose run --rm lottery-system python main.py --batch --days 30
```

### lottery-scheduler
Servicio para entrenamientos automáticos programados.

```bash
# Iniciar scheduler
docker-compose up -d lottery-scheduler

# Ver logs del scheduler
docker-compose logs -f lottery-scheduler
```

---

## 🛠️ Comandos Docker

### Construcción

```bash
# Construir imagen
docker build -t lottery-prediction:latest .

# Construir sin cache
docker build --no-cache -t lottery-prediction:latest .

# Construir con argumentos
docker build --build-arg PYTHON_VERSION=3.11 -t lottery-prediction:latest .
```

### Ejecución

```bash
# Ejecutar contenedor interactivo
docker run -it --rm lottery-prediction:latest /bin/bash

# Ejecutar comando específico
docker run --rm lottery-prediction:latest python main.py --help

# Con volúmenes montados
docker run --rm \
  -v $(pwd)/IA_models:/app/IA_models \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  lottery-prediction:latest python main.py --train
```

### Gestión

```bash
# Listar contenedores
docker ps -a

# Ver logs
docker logs lottery-system

# Entrar a contenedor en ejecución
docker exec -it lottery-system /bin/bash

# Detener contenedor
docker stop lottery-system

# Eliminar contenedor
docker rm lottery-system

# Eliminar imagen
docker rmi lottery-prediction:latest
```

---

## 📊 Docker Compose

### Servicios Definidos

```yaml
services:
  lottery-system:      # Servicio principal
  lottery-scheduler:   # Entrenamientos programados
```

### Comandos Compose

```bash
# Iniciar servicios
docker-compose up -d

# Iniciar servicio específico
docker-compose up -d lottery-system

# Ver logs
docker-compose logs -f
docker-compose logs -f lottery-scheduler

# Detener servicios
docker-compose stop

# Detener y eliminar
docker-compose down

# Reconstruir servicios
docker-compose up -d --build

# Escalar servicios
docker-compose up -d --scale lottery-system=3
```

---

## 💾 Volúmenes y Persistencia

### Volúmenes Montados

```yaml
volumes:
  - ./IA_models:/app/IA_models    # Modelos entrenados
  - ./data:/app/data              # Datos del sistema
  - ./logs:/app/logs              # Logs
  - ./.env:/app/.env:ro           # Configuración (read-only)
```

### Backup de Datos

```bash
# Backup de modelos
docker run --rm \
  -v $(pwd)/IA_models:/source \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/models-$(date +%Y%m%d).tar.gz -C /source .

# Backup de datos
docker run --rm \
  -v $(pwd)/data:/source \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/data-$(date +%Y%m%d).tar.gz -C /source .
```

### Restaurar Backup

```bash
# Restaurar modelos
docker run --rm \
  -v $(pwd)/IA_models:/target \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/models-20260227.tar.gz -C /target
```

---

## 🔒 Seguridad

### Usuario No-Root

El contenedor ejecuta como usuario `lottery` (UID 1000) por seguridad:

```dockerfile
RUN useradd -m -u 1000 lottery
USER lottery
```

### Secrets Management

```bash
# Usar Docker secrets (Swarm mode)
echo "mi_api_key" | docker secret create api_key -

# En docker-compose.yml
secrets:
  api_key:
    external: true
```

### Escaneo de Vulnerabilidades

```bash
# Escanear imagen con Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image lottery-prediction:latest

# Escanear con Docker Scout
docker scout cves lottery-prediction:latest
```

---

## 📈 Monitoreo

### Healthcheck

```bash
# Ver estado de salud
docker inspect --format='{{.State.Health.Status}}' lottery-system

# Logs de healthcheck
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' lottery-system
```

### Recursos

```bash
# Ver uso de recursos
docker stats lottery-system

# Limitar recursos
docker run --rm \
  --cpus="2" \
  --memory="2g" \
  lottery-prediction:latest python main.py --train
```

---

## 🐛 Troubleshooting

### Problema: Imagen muy grande

```bash
# Ver tamaño de capas
docker history lottery-prediction:latest

# Optimizar con multi-stage build
# Ver Dockerfile.optimized
```

### Problema: Permisos en volúmenes

```bash
# Ajustar permisos
sudo chown -R 1000:1000 IA_models data logs

# O ejecutar como root (no recomendado)
docker run --user root ...
```

### Problema: Contenedor se detiene inmediatamente

```bash
# Ver logs
docker logs lottery-system

# Ejecutar interactivamente
docker run -it lottery-prediction:latest /bin/bash
```

### Problema: No puede conectar a API

```bash
# Verificar red
docker network inspect lottery-network

# Probar conectividad
docker run --rm lottery-prediction:latest \
  curl -I https://api-resultadosloterias.com
```

---

## 🚢 Deployment en Producción

### Docker Swarm

```bash
# Inicializar swarm
docker swarm init

# Desplegar stack
docker stack deploy -c docker-compose.yml lottery

# Ver servicios
docker service ls

# Escalar servicio
docker service scale lottery_lottery-system=3

# Ver logs
docker service logs -f lottery_lottery-system
```

### Kubernetes

```bash
# Crear deployment
kubectl create deployment lottery-system \
  --image=lottery-prediction:latest

# Exponer servicio
kubectl expose deployment lottery-system --port=8000

# Ver pods
kubectl get pods

# Ver logs
kubectl logs -f deployment/lottery-system
```

---

## 📚 Mejores Prácticas

1. **Multi-stage builds**: Reducir tamaño de imagen
2. **Layer caching**: Copiar requirements.txt primero
3. **Usuario no-root**: Ejecutar como usuario sin privilegios
4. **Healthchecks**: Monitorear estado del contenedor
5. **Volúmenes**: Persistir datos importantes
6. **Variables de entorno**: Configuración flexible
7. **Logs**: Usar stdout/stderr para logs
8. **Secrets**: No incluir credenciales en imagen

---

## 🔄 CI/CD

### GitHub Actions

```yaml
name: Docker Build

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t lottery-prediction:latest .
      
      - name: Run tests
        run: docker run --rm lottery-prediction:latest python -m pytest
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push lottery-prediction:latest
```

---

## 📖 Referencias

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Estado:** ✅ Producción
