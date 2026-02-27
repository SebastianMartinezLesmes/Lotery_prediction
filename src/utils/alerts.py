"""
Sistema de alertas para monitoreo de modelos.
Notifica cuando el accuracy cae bajo umbrales configurados.
"""
import os
import json
import smtplib
from datetime import datetime
from typing import Dict, List, Optional, Callable
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.config import settings
from src.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__, "alerts.log")


class AlertLevel:
    """Niveles de alerta."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertChannel:
    """Canales de notificación disponibles."""
    CONSOLE = "console"
    FILE = "file"
    EMAIL = "email"
    WEBHOOK = "webhook"


class Alert:
    """Representa una alerta del sistema."""
    
    def __init__(
        self,
        level: str,
        title: str,
        message: str,
        lottery: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        timestamp: Optional[datetime] = None
    ):
        self.level = level
        self.title = title
        self.message = message
        self.lottery = lottery
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold = threshold
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        """Convierte la alerta a diccionario."""
        return {
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "lottery": self.lottery,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """Representación en string de la alerta."""
        return (
            f"[{self.level}] {self.title}\n"
            f"Lotería: {self.lottery}\n"
            f"Métrica: {self.metric_name}\n"
            f"Valor actual: {self.current_value:.4f}\n"
            f"Umbral: {self.threshold:.4f}\n"
            f"Mensaje: {self.message}\n"
            f"Fecha: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )


class AlertManager:
    """Gestor de alertas del sistema."""
    
    def __init__(
        self,
        enabled_channels: Optional[List[str]] = None,
        alert_file: Optional[Path] = None
    ):
        """
        Inicializa el gestor de alertas.
        
        Args:
            enabled_channels: Lista de canales habilitados
            alert_file: Archivo para guardar alertas
        """
        self.enabled_channels = enabled_channels or [AlertChannel.CONSOLE, AlertChannel.FILE]
        self.alert_file = alert_file or settings.LOGS_DIR / "alerts.json"
        self.alerts_history: List[Alert] = []
        
        # Cargar configuración de alertas desde .env
        self.thresholds = {
            "accuracy_warning": float(os.getenv("ALERT_ACCURACY_WARNING", "0.6")),
            "accuracy_critical": float(os.getenv("ALERT_ACCURACY_CRITICAL", "0.5")),
            "f1_warning": float(os.getenv("ALERT_F1_WARNING", "0.55")),
            "f1_critical": float(os.getenv("ALERT_F1_CRITICAL", "0.45"))
        }
        
        # Configuración de email (opcional)
        self.email_config = {
            "enabled": os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true",
            "smtp_server": os.getenv("ALERT_SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("ALERT_SMTP_PORT", "587")),
            "sender": os.getenv("ALERT_EMAIL_SENDER", ""),
            "password": os.getenv("ALERT_EMAIL_PASSWORD", ""),
            "recipients": os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")
        }
        
        logger.info(f"AlertManager inicializado con canales: {self.enabled_channels}")
    
    def check_accuracy(
        self,
        lottery: str,
        model_type: str,
        accuracy: float,
        f1_score: Optional[float] = None
    ) -> Optional[Alert]:
        """
        Verifica si el accuracy está bajo el umbral y genera alerta.
        
        Args:
            lottery: Nombre de la lotería
            model_type: Tipo de modelo (result/series)
            accuracy: Valor de accuracy
            f1_score: Valor de F1-score (opcional)
            
        Returns:
            Alert si se generó una alerta, None si no
        """
        alert = None
        
        # Verificar accuracy
        if accuracy < self.thresholds["accuracy_critical"]:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                title=f"Accuracy Crítico en {lottery}",
                message=f"El modelo {model_type} tiene un accuracy muy bajo ({accuracy:.4f}). "
                        f"Se requiere atención inmediata.",
                lottery=lottery,
                metric_name=f"accuracy_{model_type}",
                current_value=accuracy,
                threshold=self.thresholds["accuracy_critical"]
            )
        elif accuracy < self.thresholds["accuracy_warning"]:
            alert = Alert(
                level=AlertLevel.WARNING,
                title=f"Accuracy Bajo en {lottery}",
                message=f"El modelo {model_type} tiene un accuracy bajo ({accuracy:.4f}). "
                        f"Considere re-entrenar el modelo.",
                lottery=lottery,
                metric_name=f"accuracy_{model_type}",
                current_value=accuracy,
                threshold=self.thresholds["accuracy_warning"]
            )
        
        # Verificar F1-score si está disponible
        if f1_score is not None:
            if f1_score < self.thresholds["f1_critical"]:
                alert = Alert(
                    level=AlertLevel.CRITICAL,
                    title=f"F1-Score Crítico en {lottery}",
                    message=f"El modelo {model_type} tiene un F1-score muy bajo ({f1_score:.4f}). "
                            f"Se requiere atención inmediata.",
                    lottery=lottery,
                    metric_name=f"f1_{model_type}",
                    current_value=f1_score,
                    threshold=self.thresholds["f1_critical"]
                )
            elif f1_score < self.thresholds["f1_warning"] and alert is None:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    title=f"F1-Score Bajo en {lottery}",
                    message=f"El modelo {model_type} tiene un F1-score bajo ({f1_score:.4f}). "
                            f"Considere re-entrenar el modelo.",
                    lottery=lottery,
                    metric_name=f"f1_{model_type}",
                    current_value=f1_score,
                    threshold=self.thresholds["f1_warning"]
                )
        
        if alert:
            self.send_alert(alert)
        
        return alert
    
    def send_alert(self, alert: Alert) -> None:
        """
        Envía una alerta a través de los canales configurados.
        
        Args:
            alert: Alerta a enviar
        """
        self.alerts_history.append(alert)
        
        # Enviar a cada canal habilitado
        if AlertChannel.CONSOLE in self.enabled_channels:
            self._send_to_console(alert)
        
        if AlertChannel.FILE in self.enabled_channels:
            self._send_to_file(alert)
        
        if AlertChannel.EMAIL in self.enabled_channels and self.email_config["enabled"]:
            self._send_to_email(alert)
        
        logger.info(f"Alerta enviada: {alert.title}")
    
    def _send_to_console(self, alert: Alert) -> None:
        """Envía alerta a la consola."""
        symbol = {
            AlertLevel.INFO: ">>",
            AlertLevel.WARNING: "!!",
            AlertLevel.CRITICAL: "ERROR"
        }.get(alert.level, ">>")
        
        print(f"\n{'='*70}")
        print(f"{symbol} ALERTA: {alert.title}")
        print('='*70)
        print(f"Lotería: {alert.lottery}")
        print(f"Métrica: {alert.metric_name}")
        print(f"Valor actual: {alert.current_value:.4f}")
        print(f"Umbral: {alert.threshold:.4f}")
        print(f"Mensaje: {alert.message}")
        print('='*70)
    
    def _send_to_file(self, alert: Alert) -> None:
        """Guarda alerta en archivo JSON."""
        try:
            # Cargar alertas existentes
            alerts = []
            if self.alert_file.exists():
                with open(self.alert_file, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)
            
            # Agregar nueva alerta
            alerts.append(alert.to_dict())
            
            # Guardar
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump(alerts, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Alerta guardada en {self.alert_file}")
        
        except Exception as e:
            logger.error(f"Error al guardar alerta en archivo: {e}")
    
    def _send_to_email(self, alert: Alert) -> None:
        """Envía alerta por email."""
        if not self.email_config["sender"] or not self.email_config["recipients"]:
            logger.warning("Configuración de email incompleta, saltando envío")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config["sender"]
            msg['To'] = ", ".join(self.email_config["recipients"])
            msg['Subject'] = f"[{alert.level}] {alert.title}"
            
            body = f"""
            <html>
            <body>
                <h2>{alert.title}</h2>
                <p><strong>Nivel:</strong> {alert.level}</p>
                <p><strong>Lotería:</strong> {alert.lottery}</p>
                <p><strong>Métrica:</strong> {alert.metric_name}</p>
                <p><strong>Valor actual:</strong> {alert.current_value:.4f}</p>
                <p><strong>Umbral:</strong> {alert.threshold:.4f}</p>
                <p><strong>Mensaje:</strong> {alert.message}</p>
                <p><strong>Fecha:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["sender"], self.email_config["password"])
                server.send_message(msg)
            
            logger.info(f"Alerta enviada por email a {len(self.email_config['recipients'])} destinatarios")
        
        except Exception as e:
            logger.error(f"Error al enviar alerta por email: {e}")
    
    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        """
        Obtiene las alertas más recientes.
        
        Args:
            limit: Número máximo de alertas a retornar
            
        Returns:
            Lista de alertas recientes
        """
        return self.alerts_history[-limit:]
    
    def get_alerts_by_lottery(self, lottery: str) -> List[Alert]:
        """
        Obtiene alertas de una lotería específica.
        
        Args:
            lottery: Nombre de la lotería
            
        Returns:
            Lista de alertas de la lotería
        """
        return [alert for alert in self.alerts_history if alert.lottery == lottery]
    
    def clear_alerts(self) -> None:
        """Limpia el historial de alertas en memoria."""
        self.alerts_history.clear()
        logger.info("Historial de alertas limpiado")


# Instancia global del gestor de alertas
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Obtiene la instancia global del gestor de alertas."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def check_model_performance(
    lottery: str,
    model_type: str,
    accuracy: float,
    f1_score: Optional[float] = None
) -> Optional[Alert]:
    """
    Función de conveniencia para verificar el rendimiento de un modelo.
    
    Args:
        lottery: Nombre de la lotería
        model_type: Tipo de modelo (result/series)
        accuracy: Valor de accuracy
        f1_score: Valor de F1-score (opcional)
        
    Returns:
        Alert si se generó una alerta, None si no
    """
    manager = get_alert_manager()
    return manager.check_accuracy(lottery, model_type, accuracy, f1_score)


def main():
    """Función principal para pruebas."""
    print("Sistema de Alertas - Prueba\n")
    
    manager = AlertManager()
    
    # Simular diferentes escenarios
    print("Escenario 1: Accuracy normal (no genera alerta)")
    manager.check_accuracy("ASTRO LUNA", "result", 0.75, 0.72)
    
    print("\nEscenario 2: Accuracy bajo (WARNING)")
    manager.check_accuracy("ASTRO SOL", "series", 0.58, 0.56)
    
    print("\nEscenario 3: Accuracy crítico (CRITICAL)")
    manager.check_accuracy("ASTRO LUNA", "result", 0.45, 0.42)
    
    print("\nEscenario 4: F1-score crítico")
    manager.check_accuracy("ASTRO SOL", "series", 0.65, 0.40)
    
    # Mostrar resumen
    print(f"\n\nTotal de alertas generadas: {len(manager.alerts_history)}")
    print(f"Alertas guardadas en: {manager.alert_file}")


if __name__ == "__main__":
    main()
