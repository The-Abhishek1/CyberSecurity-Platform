from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from enum import Enum

from src.utils.logging import logger


class EscalationLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EscalationManager:
    """
    Enterprise Escalation Manager
    
    Handles escalation of issues:
    - Multi-level escalation (warning -> error -> critical)
    - Notification channels (log, email, Slack, PagerDuty)
    - Escalation policies per component
    - Automatic resolution tracking
    """
    
    def __init__(self):
        # Escalation policies
        self.policies: Dict[str, Dict] = {}
        
        # Active escalations
        self.active_escalations: Dict[str, Dict] = {}
        
        # Escalation history
        self.history: List[Dict] = []
        
        # Notification channels
        self.channels = {
            "log": self._notify_log,
            "email": self._notify_email,
            "slack": self._notify_slack,
            "pagerduty": self._notify_pagerduty,
            "webhook": self._notify_webhook
        }
        
        logger.info("Escalation Manager initialized")
    
    async def escalate(
        self,
        level: EscalationLevel,
        component: str,
        message: str,
        context: Optional[Dict] = None,
        policy_name: Optional[str] = None
    ):
        """
        Escalate an issue
        
        Args:
            level: Escalation level
            component: Component experiencing issue
            message: Description of issue
            context: Additional context
            policy_name: Escalation policy to use
        """
        
        escalation_id = f"{component}_{datetime.utcnow().timestamp()}"
        
        escalation = {
            "id": escalation_id,
            "level": level.value if isinstance(level, EscalationLevel) else level,
            "component": component,
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow(),
            "status": "active",
            "acknowledged": False,
            "resolved": False,
            "notifications_sent": []
        }
        
        # Get policy
        policy = None
        if policy_name:
            policy = self.policies.get(policy_name)
        else:
            policy = self.policies.get(f"{component}_policy")
        
        if not policy:
            # Use default policy
            policy = self._get_default_policy(level)
        
        # Apply escalation policy
        await self._apply_escalation_policy(escalation, policy)
        
        # Store escalation
        self.active_escalations[escalation_id] = escalation
        self.history.append(escalation)
        
        # Limit history size
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        logger.log(
            getattr(logging, level.value.upper()),
            f"Escalation [{level.value.upper()}] {component}: {message}",
            extra={"escalation_id": escalation_id, "context": context}
        )
    
    async def _apply_escalation_policy(self, escalation: Dict, policy: Dict):
        """Apply escalation policy"""
        
        # Get escalation steps based on level
        steps = policy.get(escalation["level"], [])
        
        for step in steps:
            # Wait for delay
            if step.get("delay", 0) > 0:
                await asyncio.sleep(step["delay"])
            
            # Send notifications
            for channel in step.get("channels", []):
                if channel in self.channels:
                    success = await self.channels[channel](escalation, step)
                    if success:
                        escalation["notifications_sent"].append({
                            "channel": channel,
                            "timestamp": datetime.utcnow(),
                            "step": step
                        })
            
            # Check if escalation was resolved
            if escalation.get("resolved"):
                break
    
    def _get_default_policy(self, level: EscalationLevel) -> Dict:
        """Get default escalation policy"""
        
        return {
            "debug": [
                {"delay": 0, "channels": ["log"]}
            ],
            "info": [
                {"delay": 0, "channels": ["log"]}
            ],
            "warning": [
                {"delay": 0, "channels": ["log"]},
                {"delay": 300, "channels": ["email"]}  # 5 minutes
            ],
            "error": [
                {"delay": 0, "channels": ["log", "email"]},
                {"delay": 600, "channels": ["slack"]}  # 10 minutes
            ],
            "critical": [
                {"delay": 0, "channels": ["log", "email", "slack"]},
                {"delay": 300, "channels": ["pagerduty"]}  # 5 minutes
            ]
        }
    
    async def register_policy(self, name: str, policy: Dict):
        """Register an escalation policy"""
        self.policies[name] = policy
        logger.info(f"Registered escalation policy: {name}")
    
    async def acknowledge(self, escalation_id: str, user: str):
        """Acknowledge an escalation"""
        
        if escalation_id in self.active_escalations:
            self.active_escalations[escalation_id]["acknowledged"] = True
            self.active_escalations[escalation_id]["acknowledged_by"] = user
            self.active_escalations[escalation_id]["acknowledged_at"] = datetime.utcnow()
            
            logger.info(f"Escalation {escalation_id} acknowledged by {user}")
    
    async def resolve(self, escalation_id: str, resolution: str):
        """Resolve an escalation"""
        
        if escalation_id in self.active_escalations:
            self.active_escalations[escalation_id]["resolved"] = True
            self.active_escalations[escalation_id]["resolution"] = resolution
            self.active_escalations[escalation_id]["resolved_at"] = datetime.utcnow()
            
            # Remove from active
            escalation = self.active_escalations.pop(escalation_id)
            
            logger.info(f"Escalation {escalation_id} resolved: {resolution}")
    
    async def _notify_log(self, escalation: Dict, step: Dict) -> bool:
        """Log the escalation"""
        # Don't use 'message' as an extra key - it conflicts with LogRecord
        log_data = {
            "escalation_id": escalation.get("id"),
            "level": step.get("level"),
            "channel": step.get("channel"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Use a different key for the message
        logger.warning(
            f"Escalation triggered: {step.get('message', 'No message')}",
            extra={"escalation_data": log_data}
        )
        return True


    async def _notify_email(self, escalation: Dict, step: Dict) -> bool:
        """Send email notification"""
        
        # In production, integrate with email service
        logger.info(f"Would send email for escalation {escalation['id']}")
        return True
    
    async def _notify_slack(self, escalation: Dict, step: Dict) -> bool:
        """Send Slack notification"""
        
        # In production, integrate with Slack webhook
        logger.info(f"Would send Slack message for escalation {escalation['id']}")
        return True
    
    async def _notify_pagerduty(self, escalation: Dict, step: Dict) -> bool:
        """Send PagerDuty notification"""
        
        # In production, integrate with PagerDuty API
        logger.info(f"Would create PagerDuty incident for escalation {escalation['id']}")
        return True
    
    async def _notify_webhook(self, escalation: Dict, step: Dict) -> bool:
        """Send webhook notification"""
        
        # In production, send to configured webhook
        logger.info(f"Would send webhook for escalation {escalation['id']}")
        return True
    
    def get_active_escalations(self) -> List[Dict]:
        """Get all active escalations"""
        return list(self.active_escalations.values())
    
    def get_escalation_history(
        self,
        component: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get escalation history"""
        
        filtered = self.history
        
        if component:
            filtered = [e for e in filtered if e["component"] == component]
        
        if level:
            filtered = [e for e in filtered if e["level"] == level]
        
        return sorted(filtered, key=lambda x: x["timestamp"], reverse=True)[:limit]