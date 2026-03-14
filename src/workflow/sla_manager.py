
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


class SLAManager:
    """Manages Service Level Agreements for workflows"""
    
    def __init__(self):
        self.slas = {}
        self.sla_tracking = {}
        self.escalation_policies = {}
        self.notification_callbacks = []
        logger.info("SLA Manager initialized")
    
    async def define_sla(self,
                         sla_id: str,
                         name: str,
                         target_seconds: int,
                         warning_threshold: float = 0.8,
                         critical_threshold: float = 1.0,
                         business_hours_only: bool = False,
                         escalation_policy: Optional[str] = None) -> Dict:
        """Define a new SLA"""
        
        sla = {
            "sla_id": sla_id,
            "name": name,
            "target_seconds": target_seconds,
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
            "business_hours_only": business_hours_only,
            "escalation_policy": escalation_policy,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.slas[sla_id] = sla
        logger.info(f"Defined SLA: {name} ({target_seconds}s)")
        
        return sla
    
    async def track_workflow(self, 
                             workflow_id: str,
                             sla_id: str,
                             start_time: Optional[datetime] = None) -> str:
        """Start tracking a workflow against an SLA"""
        
        if sla_id not in self.slas:
            raise ValueError(f"SLA {sla_id} not defined")
        
        tracking_id = f"track_{workflow_id}_{sla_id}"
        
        tracking = {
            "tracking_id": tracking_id,
            "workflow_id": workflow_id,
            "sla_id": sla_id,
            "sla": self.slas[sla_id],
            "start_time": (start_time or datetime.utcnow()).isoformat(),
            "end_time": None,
            "status": "in_progress",
            "warnings_sent": [],
            "escalations_triggered": []
        }
        
        self.sla_tracking[tracking_id] = tracking
        
        # Start monitoring task
        asyncio.create_task(self._monitor_sla(tracking_id))
        
        return tracking_id
    
    async def complete_workflow(self, tracking_id: str, success: bool = True):
        """Mark a workflow as completed"""
        
        if tracking_id not in self.sla_tracking:
            logger.error(f"Tracking ID {tracking_id} not found")
            return
        
        tracking = self.sla_tracking[tracking_id]
        tracking["end_time"] = datetime.utcnow().isoformat()
        tracking["status"] = "completed" if success else "failed"
        
        # Calculate actual duration
        start = datetime.fromisoformat(tracking["start_time"])
        end = datetime.utcnow()
        duration = (end - start).total_seconds()
        
        tracking["actual_duration"] = duration
        
        sla = tracking["sla"]
        if duration > sla["target_seconds"]:
            tracking["sla_met"] = False
            logger.warning(f"SLA breach for workflow {tracking['workflow_id']}: {duration}s > {sla['target_seconds']}s")
        else:
            tracking["sla_met"] = True
            logger.info(f"SLA met for workflow {tracking['workflow_id']}: {duration}s <= {sla['target_seconds']}s")
    
    async def _monitor_sla(self, tracking_id: str):
        """Monitor SLA compliance"""
        
        if tracking_id not in self.sla_tracking:
            return
        
        tracking = self.sla_tracking[tracking_id]
        sla = tracking["sla"]
        start_time = datetime.fromisoformat(tracking["start_time"])
        
        warning_time = start_time + timedelta(seconds=sla["target_seconds"] * sla["warning_threshold"])
        critical_time = start_time + timedelta(seconds=sla["target_seconds"] * sla["critical_threshold"])
        deadline = start_time + timedelta(seconds=sla["target_seconds"])
        
        # Monitor loop
        while tracking["status"] == "in_progress":
            now = datetime.utcnow()
            
            # Check for warning threshold
            if now >= warning_time and "warning" not in tracking["warnings_sent"]:
                await self._send_notification(
                    "sla_warning",
                    tracking,
                    f"SLA warning: {sla['name']} at {sla['warning_threshold']*100}%"
                )
                tracking["warnings_sent"].append("warning")
            
            # Check for critical threshold
            if now >= critical_time and "critical" not in tracking["warnings_sent"]:
                await self._send_notification(
                    "sla_critical",
                    tracking,
                    f"SLA critical: {sla['name']} at {sla['critical_threshold']*100}%"
                )
                tracking["warnings_sent"].append("critical")
                
                # Trigger escalation if policy exists
                if sla.get("escalation_policy"):
                    await self._trigger_escalation(tracking, sla["escalation_policy"])
            
            # Check for breach
            if now >= deadline:
                tracking["breached"] = True
                await self._send_notification(
                    "sla_breach",
                    tracking,
                    f"SLA BREACHED: {sla['name']} exceeded {sla['target_seconds']}s"
                )
                break
            
            await asyncio.sleep(5)
    
    async def _send_notification(self, notification_type: str, tracking: Dict, message: str):
        """Send SLA notification"""
        
        notification = {
            "type": notification_type,
            "workflow_id": tracking["workflow_id"],
            "sla_id": tracking["sla_id"],
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.warning(f"SLA Notification: {message}")
        
        # Call registered callbacks
        for callback in self.notification_callbacks:
            try:
                await callback(notification)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")
    
    async def register_notification_callback(self, callback):
        """Register a callback for SLA notifications"""
        self.notification_callbacks.append(callback)
    
    async def _trigger_escalation(self, tracking: Dict, policy_name: str):
        """Trigger escalation policy"""
        
        if policy_name in self.escalation_policies:
            policy = self.escalation_policies[policy_name]
            logger.info(f"Triggering escalation policy: {policy_name}")
            
            tracking["escalations_triggered"].append({
                "policy": policy_name,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def define_escalation_policy(self,
                                       policy_name: str,
                                       levels: List[Dict]) -> str:
        """Define an escalation policy"""
        
        policy = {
            "name": policy_name,
            "levels": levels,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.escalation_policies[policy_name] = policy
        logger.info(f"Defined escalation policy: {policy_name}")
        
        return policy_name
    
    async def get_sla_status(self, tracking_id: str) -> Optional[Dict]:
        """Get SLA status for a tracked workflow"""
        
        if tracking_id not in self.sla_tracking:
            return None
        
        tracking = self.sla_tracking[tracking_id]
        start = datetime.fromisoformat(tracking["start_time"])
        now = datetime.utcnow()
        elapsed = (now - start).total_seconds()
        
        sla = tracking["sla"]
        
        return {
            "tracking_id": tracking_id,
            "workflow_id": tracking["workflow_id"],
            "sla_name": sla["name"],
            "elapsed_seconds": elapsed,
            "target_seconds": sla["target_seconds"],
            "percent_used": (elapsed / sla["target_seconds"]) * 100 if sla["target_seconds"] > 0 else 0,
            "status": tracking["status"],
            "breached": tracking.get("breached", False),
            "warnings_sent": tracking["warnings_sent"]
        }