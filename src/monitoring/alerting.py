from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class AlertManager:
    """
    Enterprise Alert Manager
    
    Integrates with Prometheus AlertManager
    Features:
    - Alert routing
    - Deduplication
    - Silencing
    - Escalation
    - Notification channels
    """
    
    def __init__(self):
        self.alerts: Dict[str, Dict] = {}
        self.silences: Dict[str, Dict] = {}
        self.escalation_policies: Dict[str, List] = {}
        
        # Notification channels
        self.channels = {
            "email": self._send_email_alert,
            "slack": self._send_slack_alert,
            "pagerduty": self._send_pagerduty_alert,
            "webhook": self._send_webhook_alert
        }
        
        # Alert history
        self.history: List[Dict] = []
        
        logger.info("Alert Manager initialized")
    
    async def send_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        labels: Optional[Dict] = None,
        annotations: Optional[Dict] = None,
        channels: Optional[List[str]] = None
    ):
        """Send an alert"""
        
        alert_id = f"{name}_{datetime.utcnow().timestamp()}"
        
        alert = {
            "id": alert_id,
            "name": name,
            "severity": severity.value,
            "message": message,
            "labels": labels or {},
            "annotations": annotations or {},
            "status": AlertStatus.FIRING.value,
            "starts_at": datetime.utcnow().isoformat(),
            "ends_at": None,
            "notifications_sent": []
        }
        
        # Check for duplicates
        if await self._is_duplicate(alert):
            logger.debug(f"Duplicate alert suppressed: {name}")
            return
        
        # Check silences
        if await self._is_silenced(alert):
            logger.debug(f"Alert silenced: {name}")
            return
        
        # Store alert
        self.alerts[alert_id] = alert
        self.history.append(alert)
        
        # Send notifications
        channels = channels or ["slack", "email"]
        for channel in channels:
            if channel in self.channels:
                try:
                    success = await self.channels[channel](alert)
                    if success:
                        alert["notifications_sent"].append({
                            "channel": channel,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Failed to send {channel} alert: {e}")
        
        # Apply escalation policy
        await self._apply_escalation(alert)
        
        logger.info(f"Alert sent: {name} [{severity.value}]")
        
        return alert_id
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        
        if alert_id in self.alerts:
            self.alerts[alert_id]["status"] = AlertStatus.RESOLVED.value
            self.alerts[alert_id]["ends_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Alert resolved: {alert_id}")
    
    async def acknowledge_alert(self, alert_id: str, user: str):
        """Acknowledge an alert"""
        
        if alert_id in self.alerts:
            self.alerts[alert_id]["status"] = AlertStatus.ACKNOWLEDGED.value
            self.alerts[alert_id]["acknowledged_by"] = user
            self.alerts[alert_id]["acknowledged_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Alert acknowledged by {user}: {alert_id}")
    
    async def create_silence(
        self,
        matchers: Dict[str, str],
        duration: int,
        creator: str,
        comment: str
    ):
        """Create a silence rule"""
        
        silence_id = str(uuid.uuid4())
        
        silence = {
            "id": silence_id,
            "matchers": matchers,
            "starts_at": datetime.utcnow().isoformat(),
            "ends_at": (datetime.utcnow() + timedelta(seconds=duration)).isoformat(),
            "created_by": creator,
            "comment": comment,
            "active": True
        }
        
        self.silences[silence_id] = silence
        
        logger.info(f"Silence created: {silence_id}")
        
        return silence_id
    
    async def expire_silence(self, silence_id: str):
        """Expire a silence"""
        
        if silence_id in self.silences:
            self.silences[silence_id]["active"] = False
            logger.info(f"Silence expired: {silence_id}")
    
    async def _is_duplicate(self, alert: Dict) -> bool:
        """Check if alert is duplicate"""
        
        # Check for similar alerts in last 5 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        
        for existing in self.history[-50:]:
            existing_time = datetime.fromisoformat(existing["starts_at"])
            if existing_time < cutoff:
                continue
            
            if (existing["name"] == alert["name"] and
                existing["severity"] == alert["severity"] and
                existing.get("status") != AlertStatus.RESOLVED.value):
                return True
        
        return False
    
    async def _is_silenced(self, alert: Dict) -> bool:
        """Check if alert is silenced"""
        
        now = datetime.utcnow()
        
        for silence in self.silences.values():
            if not silence["active"]:
                continue
            
            start = datetime.fromisoformat(silence["starts_at"])
            end = datetime.fromisoformat(silence["ends_at"])
            
            if not (start <= now <= end):
                continue
            
            # Check matchers
            matches = True
            for key, value in silence["matchers"].items():
                if alert["labels"].get(key) != value:
                    matches = False
                    break
            
            if matches:
                return True
        
        return False
    
    async def _apply_escalation(self, alert: Dict):
        """Apply escalation policy"""
        
        severity = alert["severity"]
        
        # Get policy for severity
        policy = self.escalation_policies.get(severity, [])
        
        for step in policy:
            # Wait for delay
            if step.get("delay", 0) > 0:
                await asyncio.sleep(step["delay"])
            
            # Check if alert is still firing
            if alert["status"] != AlertStatus.FIRING.value:
                break
            
            # Send escalation notifications
            for channel in step.get("channels", []):
                if channel in self.channels:
                    await self.channels[channel]({
                        **alert,
                        "message": f"[ESCALATION] {alert['message']}"
                    })
    
    async def set_escalation_policy(
        self,
        severity: str,
        steps: List[Dict]
    ):
        """Set escalation policy for severity"""
        self.escalation_policies[severity] = steps
    
    async def _send_slack_alert(self, alert: Dict) -> bool:
        """Send alert to Slack"""
        
        webhook_url = settings.slack_webhook_url
        if not webhook_url:
            return False
        
        color = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "critical": "#c0392b"
        }.get(alert["severity"], "#95a5a6")
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": alert["name"],
                    "text": alert["message"],
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert["severity"],
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert["starts_at"],
                            "short": True
                        }
                    ],
                    "footer": "Security Orchestrator Alert"
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    async def _send_email_alert(self, alert: Dict) -> bool:
        """Send alert via email"""
        # In production, integrate with email service
        logger.info(f"Would send email alert: {alert['name']}")
        return True
    
    async def _send_pagerduty_alert(self, alert: Dict) -> bool:
        """Send alert to PagerDuty"""
        # In production, integrate with PagerDuty API
        logger.info(f"Would send PagerDuty alert: {alert['name']}")
        return True
    
    async def _send_webhook_alert(self, alert: Dict) -> bool:
        """Send alert to webhook"""
        
        webhook_url = settings.alert_webhook_url
        if not webhook_url:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=alert) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        return [
            a for a in self.alerts.values()
            if a["status"] == AlertStatus.FIRING.value
        ]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get alert history"""
        return sorted(self.history, key=lambda x: x["starts_at"], reverse=True)[:limit]