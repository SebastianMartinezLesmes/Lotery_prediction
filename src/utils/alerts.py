"""
Sistema de alertas para monitoreo de modelos.
Notifica por consola y, opcionalmente, por email cuando el accuracy
cae bajo los umbrales configurados.
"""
import os
import smtplib

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional

from src.core.logger import LoggerManager
from src.core.config import settings

logger = LoggerManager.get_logger(__name__)


class AlertLevel:
    INFO     = "INFO"
    WARNING  = "WARNING"
    CRITICAL = "CRITICAL"


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
        timestamp: Optional[datetime] = None,
    ):
        self.level         = level
        self.title         = title
        self.message       = message
        self.lottery       = lottery
        self.metric_name   = metric_name
        self.current_value = current_value
        self.threshold     = threshold
        self.timestamp     = timestamp or datetime.now()

    def to_dict(self) -> Dict:
        return {
            "level":         self.level,
            "title":         self.title,
            "message":       self.message,
            "lottery":       self.lottery,
            "metric_name":   self.metric_name,
            "current_value": self.current_value,
            "threshold":     self.threshold,
            "timestamp":     self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
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
    """Gestor de alertas — consola + email opcional, sin archivos."""

    def __init__(self):
        self.alerts_history: List[Alert] = []

        self.thresholds = {
            "accuracy_warning":  float(os.getenv("ALERT_ACCURACY_WARNING", "0.6")),
            "accuracy_critical": float(os.getenv("ALERT_ACCURACY_CRITICAL", "0.5")),
            "f1_warning":        float(os.getenv("ALERT_F1_WARNING", "0.55")),
            "f1_critical":       float(os.getenv("ALERT_F1_CRITICAL", "0.45")),
        }

        self.email_config = {
            "enabled":     os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true",
            "smtp_server": os.getenv("ALERT_SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port":   int(os.getenv("ALERT_SMTP_PORT", "587")),
            "sender":      os.getenv("ALERT_EMAIL_SENDER", ""),
            "password":    os.getenv("ALERT_EMAIL_PASSWORD", ""),
            "recipients":  os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(","),
        }

    def check_accuracy(
        self,
        lottery: str,
        model_type: str,
        accuracy: float,
        f1_score: Optional[float] = None,
    ) -> Optional[Alert]:
        alert = None

        if accuracy < self.thresholds["accuracy_critical"]:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                title=f"Accuracy Crítico en {lottery}",
                message=f"El modelo {model_type} tiene accuracy muy bajo ({accuracy:.4f}).",
                lottery=lottery,
                metric_name=f"accuracy_{model_type}",
                current_value=accuracy,
                threshold=self.thresholds["accuracy_critical"],
            )
        elif accuracy < self.thresholds["accuracy_warning"]:
            alert = Alert(
                level=AlertLevel.WARNING,
                title=f"Accuracy Bajo en {lottery}",
                message=f"El modelo {model_type} tiene accuracy bajo ({accuracy:.4f}).",
                lottery=lottery,
                metric_name=f"accuracy_{model_type}",
                current_value=accuracy,
                threshold=self.thresholds["accuracy_warning"],
            )

        if f1_score is not None:
            if f1_score < self.thresholds["f1_critical"]:
                alert = Alert(
                    level=AlertLevel.CRITICAL,
                    title=f"F1-Score Crítico en {lottery}",
                    message=f"El modelo {model_type} tiene F1 muy bajo ({f1_score:.4f}).",
                    lottery=lottery,
                    metric_name=f"f1_{model_type}",
                    current_value=f1_score,
                    threshold=self.thresholds["f1_critical"],
                )
            elif f1_score < self.thresholds["f1_warning"] and alert is None:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    title=f"F1-Score Bajo en {lottery}",
                    message=f"El modelo {model_type} tiene F1 bajo ({f1_score:.4f}).",
                    lottery=lottery,
                    metric_name=f"f1_{model_type}",
                    current_value=f1_score,
                    threshold=self.thresholds["f1_warning"],
                )

        if alert:
            self._send(alert)

        return alert

    def _send(self, alert: Alert) -> None:
        self.alerts_history.append(alert)
        self._to_console(alert)
        if self.email_config["enabled"]:
            self._to_email(alert)
        logger.info(f"Alerta: {alert.title}")

    def _to_console(self, alert: Alert) -> None:
        symbol = {"INFO": ">>", "WARNING": "!!", "CRITICAL": "ERROR"}.get(alert.level, ">>")
        print(f"\n{'='*70}")
        print(f"{symbol} ALERTA: {alert.title}")
        print("=" * 70)
        print(f"Lotería: {alert.lottery}")
        print(f"Métrica: {alert.metric_name}")
        print(f"Valor actual: {alert.current_value:.4f}")
        print(f"Umbral: {alert.threshold:.4f}")
        print(f"Mensaje: {alert.message}")
        print("=" * 70)

    def _to_email(self, alert: Alert) -> None:
        if not self.email_config["sender"] or not self.email_config["recipients"]:
            logger.warning("Configuración de email incompleta, saltando envío")
            return
        try:
            msg = MIMEMultipart()
            msg["From"]    = self.email_config["sender"]
            msg["To"]      = ", ".join(self.email_config["recipients"])
            msg["Subject"] = f"[{alert.level}] {alert.title}"
            body = (
                f"<html><body>"
                f"<h2>{alert.title}</h2>"
                f"<p><b>Nivel:</b> {alert.level}</p>"
                f"<p><b>Lotería:</b> {alert.lottery}</p>"
                f"<p><b>Métrica:</b> {alert.metric_name}</p>"
                f"<p><b>Valor actual:</b> {alert.current_value:.4f}</p>"
                f"<p><b>Umbral:</b> {alert.threshold:.4f}</p>"
                f"<p><b>Mensaje:</b> {alert.message}</p>"
                f"<p><b>Fecha:</b> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>"
                f"</body></html>"
            )
            msg.attach(MIMEText(body, "html"))
            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as s:
                s.starttls()
                s.login(self.email_config["sender"], self.email_config["password"])
                s.send_message(msg)
            logger.info(f"Alerta enviada por email")
        except Exception as e:
            logger.error(f"Error al enviar alerta por email: {e}")

    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        return self.alerts_history[-limit:]

    def get_alerts_by_lottery(self, lottery: str) -> List[Alert]:
        return [a for a in self.alerts_history if a.lottery == lottery]

    def clear_alerts(self) -> None:
        self.alerts_history.clear()


# ── Instancia global ──────────────────────────────────────────────────
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def check_model_performance(
    lottery: str,
    model_type: str,
    accuracy: float,
    f1_score: Optional[float] = None,
) -> Optional[Alert]:
    return get_alert_manager().check_accuracy(lottery, model_type, accuracy, f1_score)
