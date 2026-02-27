# 🚨 Sistema de Alertas

## Descripción

El **Sistema de Alertas** monitorea automáticamente el rendimiento de los modelos de Machine Learning y notifica cuando las métricas caen bajo umbrales configurados, permitiendo una respuesta rápida ante problemas de calidad.

---

## ✨ Características

- **Monitoreo automático**: Verifica accuracy y F1-score después de cada entrenamiento
- **Múltiples niveles**: INFO, WARNING, CRITICAL
- **Canales configurables**: Consola, archivo, email, webhook
- **Umbrales personalizables**: Configura tus propios límites vía `.env`
- **Historial completo**: Todas las alertas se guardan en JSON
- **Filtros avanzados**: Por lotería, nivel, fecha
- **Reportes estadísticos**: Análisis de tendencias y patrones

---

## 🎯 Niveles de Alerta

### INFO
- Información general del sistema
- No requiere acción inmediata

### WARNING (⚠️)
- Accuracy < 0.6 (configurable)
- F1-score < 0.55 (configurable)
- Requiere atención: considerar re-entrenamiento

### CRITICAL (❌)
- Accuracy < 0.5 (configurable)
- F1-score < 0.45 (configurable)
- Requiere acción inmediata: modelo no confiable

---

## ⚙️ Configuración

### 1. Archivo `.env`

```env
# Alert System Configuration
ALERT_ACCURACY_WARNING=0.6
ALERT_ACCURACY_CRITICAL=0.5
ALERT_F1_WARNING=0.55
ALERT_F1_CRITICAL=0.45

# Email Alerts (opcional)
ALERT_EMAIL_ENABLED=false
ALERT_SMTP_SERVER=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_EMAIL_SENDER=tu_email@gmail.com
ALERT_EMAIL_PASSWORD=tu_contraseña_app
ALERT_EMAIL_RECIPIENTS=destinatario1@email.com,destinatario2@email.com
```

### 2. Umbrales Recomendados

| Métrica | WARNING | CRITICAL | Descripción |
|---------|---------|----------|-------------|
| Accuracy | 0.6 | 0.5 | Precisión general del modelo |
| F1-Score | 0.55 | 0.45 | Balance entre precisión y recall |

**Ajusta según tu caso de uso:**
- Más estricto: WARNING=0.7, CRITICAL=0.6
- Más permisivo: WARNING=0.5, CRITICAL=0.4

---

## 🚀 Uso Automático

El sistema se activa automáticamente durante el entrenamiento:

```bash
# Entrenar modelos (alertas automáticas)
python main.py --train
```

**Salida con alerta:**
```
======================================================================
!! ALERTA: Accuracy Bajo en ASTRO LUNA
======================================================================
Lotería: ASTRO LUNA
Métrica: accuracy_result
Valor actual: 0.5800
Umbral: 0.6000
Mensaje: El modelo result tiene un accuracy bajo (0.5800). 
         Considere re-entrenar el modelo.
======================================================================
```

---

## 📊 Visualización de Alertas

### Ver alertas recientes

```bash
# Últimas 10 alertas (default)
python scripts/ver_alertas.py

# Últimas 20 alertas
python scripts/ver_alertas.py --recent 20
```

### Filtrar por lotería

```bash
python scripts/ver_alertas.py --lottery "ASTRO LUNA"
```

### Filtrar por nivel

```bash
# Solo alertas críticas
python scripts/ver_alertas.py --level CRITICAL

# Solo warnings
python scripts/ver_alertas.py --level WARNING
```

### Filtrar por fecha

```bash
# Últimos 7 días
python scripts/ver_alertas.py --days 7

# Último mes
python scripts/ver_alertas.py --days 30
```

### Generar reporte

```bash
python scripts/ver_alertas.py --report
```

**Salida del reporte:**
```
======================================================================
REPORTE DE ALERTAS
======================================================================

Total de alertas: 15

Por nivel:
  WARNING    |   8 ( 53.3%)
  CRITICAL   |   5 ( 33.3%)
  INFO       |   2 ( 13.3%)

Por lotería:
  ASTRO LUNA     |   8 ( 53.3%)
  ASTRO SOL      |   7 ( 46.7%)

Por métrica:
  accuracy_result    |   6 ( 40.0%)
  accuracy_series    |   5 ( 33.3%)
  f1_result          |   4 ( 26.7%)

!! Alertas críticas: 5
   Requieren atención inmediata:
   - ASTRO LUNA: accuracy_result = 0.4500
   - ASTRO SOL: f1_series = 0.4200

Tendencia temporal:
  Primera alerta: 2026-02-20 10:30
  Última alerta:  2026-02-27 15:45
  Período: 8 días
  Promedio: 1.9 alertas/día
======================================================================
```

---

## 📧 Configuración de Email

### 1. Gmail (recomendado)

1. Habilitar autenticación de 2 factores en tu cuenta Gmail
2. Generar contraseña de aplicación:
   - Ir a: https://myaccount.google.com/apppasswords
   - Crear contraseña para "Correo"
3. Configurar `.env`:

```env
ALERT_EMAIL_ENABLED=true
ALERT_SMTP_SERVER=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_EMAIL_SENDER=tu_email@gmail.com
ALERT_EMAIL_PASSWORD=contraseña_app_generada
ALERT_EMAIL_RECIPIENTS=destinatario@email.com
```

### 2. Otros Proveedores

**Outlook/Hotmail:**
```env
ALERT_SMTP_SERVER=smtp-mail.outlook.com
ALERT_SMTP_PORT=587
```

**Yahoo:**
```env
ALERT_SMTP_SERVER=smtp.mail.yahoo.com
ALERT_SMTP_PORT=587
```

**Servidor personalizado:**
```env
ALERT_SMTP_SERVER=smtp.tuservidor.com
ALERT_SMTP_PORT=587
```

---

## 🔧 Uso Programático

### Verificar rendimiento manualmente

```python
from src.utils.alerts import check_model_performance

# Verificar un modelo
alert = check_model_performance(
    lottery="ASTRO LUNA",
    model_type="result",
    accuracy=0.55,
    f1_score=0.52
)

if alert:
    print(f"Alerta generada: {alert.title}")
```

### Usar el gestor de alertas

```python
from src.utils.alerts import AlertManager, AlertLevel

# Crear gestor
manager = AlertManager(
    enabled_channels=["console", "file", "email"]
)

# Verificar múltiples modelos
manager.check_accuracy("ASTRO LUNA", "result", 0.58, 0.55)
manager.check_accuracy("ASTRO SOL", "series", 0.45, 0.42)

# Ver alertas recientes
recent = manager.get_recent_alerts(limit=5)
for alert in recent:
    print(alert)

# Filtrar por lotería
luna_alerts = manager.get_alerts_by_lottery("ASTRO LUNA")
print(f"Alertas de ASTRO LUNA: {len(luna_alerts)}")
```

### Crear alerta personalizada

```python
from src.utils.alerts import Alert, AlertLevel, AlertManager

# Crear alerta
alert = Alert(
    level=AlertLevel.WARNING,
    title="Modelo desactualizado",
    message="El modelo no se ha entrenado en 30 días",
    lottery="ASTRO LUNA",
    metric_name="days_since_training",
    current_value=30,
    threshold=7
)

# Enviar
manager = AlertManager()
manager.send_alert(alert)
```

---

## 📁 Archivo de Alertas

### Ubicación
```
logs/alerts.json
```

### Formato

```json
[
  {
    "level": "WARNING",
    "title": "Accuracy Bajo en ASTRO LUNA",
    "message": "El modelo result tiene un accuracy bajo (0.5800)...",
    "lottery": "ASTRO LUNA",
    "metric_name": "accuracy_result",
    "current_value": 0.58,
    "threshold": 0.6,
    "timestamp": "2026-02-27T15:30:45.123456"
  }
]
```

### Gestión

```bash
# Ver alertas
python scripts/ver_alertas.py

# Limpiar alertas (requiere confirmación)
python scripts/ver_alertas.py --clear --confirm
```

---

## 🎯 Casos de Uso

### 1. Monitoreo Continuo

```bash
# Entrenar y monitorear automáticamente
python main.py --train

# Ver si hay alertas críticas
python scripts/ver_alertas.py --level CRITICAL
```

### 2. Análisis Post-Entrenamiento

```bash
# Después de entrenar, revisar alertas
python scripts/ver_alertas.py --days 1

# Generar reporte
python scripts/ver_alertas.py --report
```

### 3. Notificaciones por Email

```env
# Configurar en .env
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENTS=equipo@empresa.com
```

```bash
# Entrenar (envía emails automáticamente si hay alertas)
python main.py --train
```

### 4. Integración con CI/CD

```bash
#!/bin/bash
# Script de CI/CD

# Entrenar modelos
python main.py --train

# Verificar alertas críticas
CRITICAL_COUNT=$(python scripts/ver_alertas.py --level CRITICAL --days 1 | grep -c "CRITICAL")

if [ $CRITICAL_COUNT -gt 0 ]; then
    echo "ERROR: Se encontraron $CRITICAL_COUNT alertas críticas"
    exit 1
fi

echo "OK: No hay alertas críticas"
```

---

## 🔍 Detalles Técnicos

### Arquitectura

```
AlertManager
├── check_accuracy()        # Verifica métricas
├── send_alert()            # Envía a canales
├── _send_to_console()      # Consola
├── _send_to_file()         # JSON
├── _send_to_email()        # Email
└── get_recent_alerts()     # Consultas
```

### Flujo de Alertas

```
1. Entrenamiento completa
   └─> training.py

2. Verificar métricas
   └─> check_model_performance()

3. Comparar con umbrales
   └─> AlertManager.check_accuracy()

4. Generar alerta si necesario
   └─> Alert()

5. Enviar a canales
   ├─> Consola (print)
   ├─> Archivo (JSON)
   └─> Email (SMTP)

6. Guardar en historial
   └─> alerts_history[]
```

### Integración con Training

El sistema se integra automáticamente en `src/utils/training.py`:

```python
# Al final del entrenamiento
check_model_performance(nombre_loteria, "result", acc_result, f1_result)
check_model_performance(nombre_loteria, "series", acc_series, f1_series)
```

---

## 📊 Métricas Monitoreadas

### Accuracy
- **Qué mide**: Porcentaje de predicciones correctas
- **Rango**: 0.0 - 1.0 (0% - 100%)
- **Umbral WARNING**: < 0.6
- **Umbral CRITICAL**: < 0.5

### F1-Score
- **Qué mide**: Balance entre precisión y recall
- **Rango**: 0.0 - 1.0
- **Umbral WARNING**: < 0.55
- **Umbral CRITICAL**: < 0.45

### Modelos Monitoreados
- **result**: Predicción de números
- **series**: Predicción de símbolos

---

## 🚨 Solución de Problemas

### No se generan alertas

1. Verificar que las métricas estén bajo el umbral:
```bash
python scripts/verificar_ia_models.py
```

2. Verificar configuración en `.env`:
```bash
python main.py --config
```

3. Revisar logs:
```bash
cat logs/training.log | grep -i alert
```

### Emails no se envían

1. Verificar configuración:
```env
ALERT_EMAIL_ENABLED=true  # Debe ser true
ALERT_EMAIL_SENDER=tu_email@gmail.com  # No vacío
ALERT_EMAIL_PASSWORD=contraseña_app  # Contraseña de aplicación
```

2. Probar conexión SMTP:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('tu_email@gmail.com', 'contraseña_app')
print("Conexión exitosa")
```

3. Revisar logs de errores:
```bash
cat logs/log_loteria.log | grep -i email
```

### Demasiadas alertas

Ajustar umbrales en `.env`:
```env
# Más permisivo
ALERT_ACCURACY_WARNING=0.5
ALERT_ACCURACY_CRITICAL=0.4
```

---

## 📈 Próximas Mejoras

- [ ] Integración con Slack/Discord
- [ ] Webhooks personalizados
- [ ] Dashboard web de alertas
- [ ] Alertas por SMS
- [ ] Reglas de alerta personalizadas
- [ ] Silenciar alertas temporalmente
- [ ] Escalamiento automático de alertas
- [ ] Integración con PagerDuty/Opsgenie

---

## 📚 Ver También

- [COMO_FUNCIONA_ENTRENAMIENTO.md](COMO_FUNCIONA_ENTRENAMIENTO.md)
- [GESTION_LOGS_ENTRENAMIENTO.md](GESTION_LOGS_ENTRENAMIENTO.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Estado:** ✅ Producción
